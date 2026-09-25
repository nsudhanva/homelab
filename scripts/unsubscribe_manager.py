#!/usr/bin/env python3
"""Intelligent automated email unsubscription manager.

Scans for promotional, ad, and marketing emails across personal and family
accounts, identifies RFC 8058 One-Click and HTTPS unsubscribe endpoints,
protects essential transactional/utility/health senders, and executes
automated unsubscriptions.
"""

import argparse
import base64
import concurrent.futures
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass

# Essential senders / domains that must NEVER be unsubscribed
PROTECTED_DOMAINS = {
    # Healthcare & Medical
    "sutterhealth.org",
    "challiance.org",
    "questdiagnostics.com",
    "labcorp.com",
    "kaiserpermanente.org",
    "urgentcare",
    # Government & Identity
    "informeddelivery.usps.com",
    "usps.com",
    "dmv.ca.gov",
    "dmvonlineservices.ca.gov",
    "uidai.gov.in",
    "incometax.gov.in",
    "irs.gov",
    "seattle.gov",
    # Financial & Banking
    "chase.com",
    "discover.com",
    "bankofamerica.com",
    "wellsfargo.com",
    "citi.com",
    "citibank.com",
    "hdfcbank.com",
    "icicibank.com",
    "robinhood.com",
    "fidelity.com",
    "vanguard.com",
    "schwab.com",
    "paypal.com",
    "venmo.com",
    "zellepay.com",
    "splitwise.com",
    "renttrack.com",
    # Utilities & Core Services
    "pge.com",
    "billpay.pge.com",
    "xfinity.com",
    "comcast.net",
    "svcleanenergy.org",
    "svcea.ca.gov",
    # Authentication & Security
    "accounts.google.com",
    "google.com",
    "apple.com",
    "email.apple.com",
    "microsoft.com",
    # Critical Legal / Work / Housing / Insurance
    "bal.com",
    "balglobal.com",
    "graebel.com",
    "realpage.com",
    "loftliving.com",
    "eversource.com",
    "securian.com",
    "geico.com",
    "sbilife.co.in",
    "paze.com",
    "whoop.com",
    "amazon.com",
    "gmail.com",
}


@dataclass
class UnsubscribeTarget:
    domain: str
    sender_name: str
    sender_email: str
    message_count: int
    sample_subject: str
    unsub_url: str | None
    is_one_click: bool
    status: str = "PENDING"


def get_token(account: str) -> str:
    """Fetch OAuth access token for the given account from k8s secret or env."""
    raw = subprocess.check_output(
        [
            "kubectl",
            "get",
            "secret",
            "-n",
            "gmail-classifier",
            f"gmail-credentials-{account}",
            "-o",
            "json",
        ],
        stderr=subprocess.DEVNULL,
    )
    data = json.loads(raw)["data"]
    cid = base64.b64decode(data.get("client_id") or data["GMAIL_CLIENT_ID"]).decode()
    csec = base64.b64decode(
        data.get("client_secret") or data["GMAIL_CLIENT_SECRET"]
    ).decode()
    rtok = base64.b64decode(
        data.get("refresh_token") or data["GMAIL_REFRESH_TOKEN"]
    ).decode()

    url = "https://oauth2.googleapis.com/token"
    payload = urllib.parse.urlencode(
        {
            "client_id": cid,
            "client_secret": csec,
            "refresh_token": rtok,
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")
    req = urllib.request.Request(url, data=payload, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))["access_token"]


def is_protected(domain: str, email: str) -> bool:
    """Check if sender belongs to protected essential list."""
    dom_lower = domain.lower()
    email_lower = email.lower()
    for prot in PROTECTED_DOMAINS:
        if prot in dom_lower or prot in email_lower:
            return True
    return False


def extract_https_url(unsub_header: str | None) -> str | None:
    """Extract HTTPS unsubscribe URL from List-Unsubscribe header."""
    if not unsub_header:
        return None
    # List-Unsubscribe typically looks like <mailto:...>, <https://...>
    urls = re.findall(r"<(https?://[^>]+)>", unsub_header)
    for u in urls:
        if u.startswith(("https://", "http://")):
            return u
    # Plain url match fallback
    match = re.search(r"https?://[^\s,>]+", unsub_header)
    return match.group(0) if match else None


def scan_promotional_senders(
    token: str, account_name: str, max_messages: int = 500
) -> list[UnsubscribeTarget]:
    """Scan account for promotional senders and extract unsubscribe metadata."""
    query = "category:promotions OR label:Newsletters"
    msgs = []
    page_token = None
    while len(msgs) < max_messages:
        batch_size = min(500, max_messages - len(msgs))
        params = {"q": query, "maxResults": batch_size}
        if page_token:
            params["pageToken"] = page_token
        url = (
            "https://gmail.googleapis.com/gmail/v1/users/me/messages?"
            + urllib.parse.urlencode(params)
        )
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            batch = data.get("messages", [])
            msgs.extend(batch)
            page_token = data.get("nextPageToken")
            if not page_token or not batch:
                break

    print(
        f"[{account_name}] Found {len(msgs)} promotional messages. Inspecting headers in parallel..."
    )

    def fetch_meta(m: dict) -> dict | None:
        mid = m["id"]
        m_url = (
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}"
            "?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=List-Unsubscribe&metadataHeaders=List-Unsubscribe-Post"
        )
        m_req = urllib.request.Request(
            m_url, headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(m_req, timeout=10) as m_resp:
                d = json.loads(m_resp.read().decode("utf-8"))
                headers = {
                    h["name"]: h["value"]
                    for h in d.get("payload", {}).get("headers", [])
                }
                return {
                    "id": mid,
                    "from": headers.get("From", "Unknown"),
                    "subject": headers.get("Subject", "No Subject"),
                    "unsub": headers.get("List-Unsubscribe"),
                    "unsub_post": headers.get("List-Unsubscribe-Post"),
                }
        except Exception:  # noqa: BLE001
            return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        items = [i for i in executor.map(fetch_meta, msgs) if i]

    grouped = defaultdict(list)
    for it in items:
        sender = it["from"]
        match = re.search(r"<([^>]+)>", sender)
        email = match.group(1) if match else sender.strip()
        domain = email.split("@")[-1].lower() if "@" in email else email
        grouped[domain].append((sender, email, it))

    targets: list[UnsubscribeTarget] = []
    for domain, records in grouped.items():
        sender_full, email, first_it = records[0]
        if is_protected(domain, email):
            continue

        # Find the best unsubscribe link among all messages from this sender
        best_unsub_url = None
        is_one_click = False
        sample_subject = first_it["subject"]

        for _, _, it in records:
            unsub_header = it.get("unsub")
            post_header = it.get("unsub_post")
            url_candidate = extract_https_url(unsub_header)
            if url_candidate:
                best_unsub_url = url_candidate
                if post_header and "One-Click" in post_header:
                    is_one_click = True
                    break

        sender_name = sender_full.split("<")[0].strip().replace('"', "") or domain
        targets.append(
            UnsubscribeTarget(
                domain=domain,
                sender_name=sender_name,
                sender_email=email,
                message_count=len(records),
                sample_subject=sample_subject,
                unsub_url=best_unsub_url,
                is_one_click=is_one_click,
            )
        )

    targets.sort(key=lambda t: t.message_count, reverse=True)
    return targets


def execute_unsubscribe(target: UnsubscribeTarget) -> tuple[bool, str]:
    """Execute automated unsubscribe via RFC 8058 POST or HTTP GET."""
    if not target.unsub_url:
        return False, "No unsubscribe URL found"

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }

    try:
        if target.is_one_click:
            # RFC 8058 specification: HTTP POST with body "List-Unsubscribe=One-Click"
            payload = b"List-Unsubscribe=One-Click"
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            req = urllib.request.Request(
                target.unsub_url, data=payload, headers=headers, method="POST"
            )
        else:
            # Standard HTTPS link: HTTP GET
            req = urllib.request.Request(
                target.unsub_url, headers=headers, method="GET"
            )

        with urllib.request.urlopen(req, timeout=12) as resp:
            status_code = resp.status
            if 200 <= status_code < 400:
                method_name = (
                    "RFC 8058 One-Click" if target.is_one_click else "HTTP GET"
                )
                return True, f"Success ({status_code} via {method_name})"
            return False, f"HTTP {status_code}"
    except urllib.error.HTTPError as e:
        # Some servers return 204 or redirect, or 405 if expecting GET instead of POST
        if e.code in (200, 204, 301, 302, 303, 307, 308):
            return True, f"Success ({e.code})"
        return False, f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return False, f"Network error: {str(e)[:50]}"


def run_manager(account: str, max_messages: int = 500, execute: bool = False) -> None:
    token = get_token(account)
    targets = scan_promotional_senders(
        token, account.upper(), max_messages=max_messages
    )

    print("\n=======================================================")
    print(f"   UNSUBSCRIBE REPORT FOR ACCOUNT: {account.upper()}")
    print("=======================================================")
    print(f"Found {len(targets)} eligible promotional / marketing senders:\n")

    unsub_ready = [t for t in targets if t.unsub_url]
    manual_needed = [t for t in targets if not t.unsub_url]

    for i, t in enumerate(targets, 1):
        mechanism = (
            "⚡ RFC 8058 One-Click"
            if t.is_one_click
            else ("🌐 HTTPS Link" if t.unsub_url else "❌ No HTTP header")
        )
        print(f"{i:2d}. [{t.message_count:3d} msgs] {t.sender_name:28} ({t.domain})")
        print(f"    Subject: {t.sample_subject[:55]}")
        print(f"    Method : {mechanism}")
        if t.unsub_url:
            print(f"    Link   : {t.unsub_url[:75]}...")
        print()

    print(
        f"Summary: {len(unsub_ready)} senders ready for automated unsubscribe, {len(manual_needed)} require manual/filter handling."
    )

    if not execute:
        print(
            "\n[DRY RUN COMPLETE] Run with --execute to dispatch unsubscribe requests."
        )
        return

    print("\nExecuting automated unsubscriptions...")
    success_count = 0
    fail_count = 0

    for t in unsub_ready:
        ok, msg = execute_unsubscribe(t)
        time.sleep(0.3)
        if ok:
            success_count += 1
            print(f"  ✅ [SUCCESS] {t.sender_name} ({t.domain}): {msg}")
        else:
            fail_count += 1
            print(f"  ⚠️  [FAILED]  {t.sender_name} ({t.domain}): {msg}")

    print(
        f"\nCompleted: {success_count} unsubscribed successfully, {fail_count} failed."
    )


def main():
    parser = argparse.ArgumentParser(
        description="Automated promotional unsubscribe manager"
    )
    parser.add_argument(
        "--account", choices=["personal", "family", "both"], default="both"
    )
    parser.add_argument("--max-messages", type=int, default=500)
    parser.add_argument(
        "--execute", action="store_true", help="Execute automated unsubscribe requests"
    )
    args = parser.parse_args()

    accounts = ["personal", "family"] if args.account == "both" else [args.account]
    for acc in accounts:
        run_manager(acc, max_messages=args.max_messages, execute=args.execute)


if __name__ == "__main__":
    main()
