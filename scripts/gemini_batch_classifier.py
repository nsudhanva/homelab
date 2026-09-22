#!/usr/bin/env python3
"""Interactive batch classifier assistant for Gemini pair-programming.

1. `fetch <count>`: Fetches <count> unprocessed emails, extracts metadata in parallel,
   and writes to /tmp/batch_to_classify.json for Gemini to inspect.
2. `apply`: Reads Gemini's decisions from /tmp/batch_classified.json and applies labels
   in bulk via Gmail API batchModify, auto-archiving items older than 90 days.
"""

import argparse
import base64
import concurrent.futures
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

INPUT_FILE = Path("/tmp/batch_to_classify.json")
OUTPUT_FILE = Path("/tmp/batch_classified.json")


def get_credentials(account: str = "family") -> tuple[str, str, str]:
    cid = os.getenv("GMAIL_CLIENT_ID")
    csec = os.getenv("GMAIL_CLIENT_SECRET")
    rtok = os.getenv("GMAIL_REFRESH_TOKEN")
    if cid and csec and rtok:
        return cid, csec, rtok
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
    return cid, csec, rtok


def get_token(account: str = "family") -> str:
    cid, csec, rtok = get_credentials(account)
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


def get_labels(token: str) -> dict[str, str]:
    url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return {lbl["name"]: lbl["id"] for lbl in data.get("labels", [])}


def ensure_label(token: str, label_name: str, existing_labels: dict[str, str]) -> str:
    if label_name in existing_labels:
        return existing_labels[label_name]
    url = "https://gmail.googleapis.com/gmail/v1/users/me/labels"
    payload = json.dumps(
        {
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        created = json.loads(resp.read().decode("utf-8"))
        existing_labels[label_name] = created["id"]
        print(f"Created label '{label_name}' (ID: {created['id']})")
        return created["id"]


def fetch_batch(token: str, count: int = 50) -> list[dict]:
    url = (
        "https://gmail.googleapis.com/gmail/v1/users/me/messages?"
        + urllib.parse.urlencode(
            {
                "q": "in:inbox -label:ai-processed",
                "maxResults": count,
            }
        )
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        msgs = json.loads(resp.read().decode("utf-8")).get("messages", [])

    if not msgs:
        print("No unprocessed messages found in INBOX!")
        return []

    print(f"Retrieved {len(msgs)} message IDs. Fetching metadata concurrently...")
    items = []

    def fetch_single(m: dict) -> dict | None:
        mid = m["id"]
        m_url = (
            f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{mid}"
            "?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date"
        )
        m_req = urllib.request.Request(
            m_url, headers={"Authorization": f"Bearer {token}"}
        )
        try:
            with urllib.request.urlopen(m_req, timeout=15) as m_resp:
                data = json.loads(m_resp.read().decode("utf-8"))
                headers = {
                    h["name"]: h["value"]
                    for h in data.get("payload", {}).get("headers", [])
                }
                int_date = int(data.get("internalDate", 0)) / 1000.0
                return {
                    "id": mid,
                    "from": headers.get("From", "Unknown"),
                    "subject": headers.get("Subject", "No Subject"),
                    "snippet": data.get("snippet", "")[:120],
                    "date_ts": int_date,
                }
        except Exception:  # noqa: BLE001
            return {
                "id": mid,
                "from": "Unknown",
                "subject": "Unknown",
                "snippet": "",
                "date_ts": 0,
            }

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        items = [item for item in executor.map(fetch_single, msgs) if item]

    INPUT_FILE.write_text(json.dumps(items, indent=2))
    print(f"Saved {len(items)} items to {INPUT_FILE}")
    return items


def classify_item(item: dict) -> tuple[str, str]:
    sender = item.get("from", "").lower()
    subject = item.get("subject", "").lower()

    # 1. Travel
    travel_senders = [
        "airline",
        "delta",
        "southwest",
        "hyatt",
        "ihg",
        "hotel",
        "chase travel",
        "united",
        "alaskaair",
        "marriott",
        "hilton",
        "expedia",
        "booking.com",
        "jetblue",
        "airfrance",
        "britishairways",
        "emirates",
        "singaporeair",
        "sheraton",
        "westin",
        "airbnb",
        "vrbo",
        "kayak",
        "priceline",
        "hertz",
        "enterprise",
        "avis",
        "budget",
        "nationalcar",
        "alamo",
        "sixt",
    ]
    travel_subjects = [
        "boarding pass",
        "flight",
        "check in for your flight",
        "trip to",
        "departure gate",
        "san francisco",
        "buffalo",
        "hotel reservation",
        "itinerary",
        "e-ticket",
        "booking confirmation",
    ]
    if any(k in sender for k in travel_senders) or any(
        k in subject for k in travel_subjects
    ):
        return "Travel", "Airline, hotel, or flight travel confirmation/notification"

    # 2. Finance
    finance_senders = [
        "discover",
        "hdfc",
        "robinhood",
        "splitwise",
        "renttrack",
        "fidelity",
        "incometax",
        "billpay.pge.com",
        "paypal",
        "experian",
        "sbi life",
        "citi",
        "citibank",
        "bank of america",
        "bofa",
        "wellsfargo",
        "wells fargo",
        "capital one",
        "capitalone",
        "santander",
        "barclays",
        "hsbc",
        "icici",
        "axis bank",
        "sbi",
        "state bank",
        "vanguard",
        "schwab",
        "empower",
        "merrill",
        "etrade",
        "e*trade",
        "morgan stanley",
        "venmo",
        "zelle",
        "cash app",
        "affirm",
        "klarna",
        "equifax",
        "transunion",
        "credit karma",
        "google pay",
        "google-pay",
        "apple card",
        "paytm",
        "phonepe",
        "satish prasad",
        "seattle.gov",
    ]
    finance_subjects = [
        "statement is available",
        "paperless statement",
        "tax invoice",
        "bill is ready",
        "bill is available",
        "payment confirmation",
        "payment received",
        "funds transfer",
        "direct deposit",
        "automatic payment",
        "fico® score",
        "credit score",
        "credit profile",
        "credit file",
        "credit alert",
        "it return",
        "refund has been credited",
        "autopay",
    ]
    if (
        any(k in sender for k in finance_senders)
        or ("chase" in sender and not any(k in sender for k in ["travel"]))
        or (
            "pge.com" in sender
            and any(
                k in subject
                for k in ["autopay", "bill", "statement", "paperless", "credit"]
            )
        )
        or ("xfinity" in sender and any(k in subject for k in ["bill", "payment"]))
        or any(k in subject for k in finance_subjects)
    ):
        return (
            "Finance",
            "Financial statement, credit alert, banking, or utility bill notification",
        )

    # 3. Entertainment
    ent_senders = [
        "stubhub",
        "td garden",
        "ticketmaster",
        "seatgeek",
        "eventbrite",
        "livenation",
        "peacock",
        "netflix",
        "spotify",
        "hulu",
        "disney",
        "paramount",
        "hbo",
        "max.com",
        "youtube tv",
        "apple tv",
        "crunchyroll",
        "audible",
        "twitch",
        "nintendo",
        "playstation",
        "xbox",
        "steam",
        "amc theatres",
        "fandango",
        "regal",
    ]
    if any(k in sender for k in ent_senders) or any(
        k in subject for k in ["wwe offer", "concert", "movie ticket"]
    ):
        return (
            "Entertainment",
            "Ticketing, live events, or streaming entertainment service",
        )

    # 4. Shopping
    shopping_senders = [
        "waymo receipts",
        "lyft receipts",
        "domino",
        "doordash",
        "ubereats",
        "uber eats",
        "sephora",
        "instacart",
        "amazon",
        "uber one",
        "walmart",
        "target",
        "apple store",
        "ebay",
        "best buy",
        "costco",
        "ulta",
        "ikea",
        "homedepot",
        "home depot",
        "lowe's",
        "nordstrom",
        "macys",
        "nike",
        "adidas",
        "lululemon",
        "zara",
        "uniqlo",
        "patagonia",
        "rei.com",
        "chewy",
        "etsy",
        "grubhub",
        "postmates",
        "starbucks",
        "sweetgreen",
        "chipotle",
        "caviar",
    ]
    shopping_subjects = [
        "order confirmation",
        "your order has shipped",
        "delivered:",
        "receipt for your",
        "order #",
        "package delivered",
        "tracking number",
    ]
    if (
        any(k in sender for k in shopping_senders)
        or ("waymo" in sender and "receipt" in subject)
        or any(k in subject for k in shopping_subjects)
    ):
        return "Shopping", "Transactional receipt or shopping/order confirmation"

    # 5. Work
    work_senders = [
        "jobot",
        "forecareer",
        "infinitus",
        "kastle",
        "interview",
        "morgan stanley at work",
        "eduxlabs",
        "agentic ai",
        "qml",
        "luma-mail",
        "linkedin",
        "greenhouse",
        "lever.co",
        "workday",
        "indeed",
        "glassdoor",
        "ziprecruiter",
        "handshake",
        "hired.com",
        "bal.com",
        "balglobal.com",
        "graebel.com",
    ]
    work_subjects = [
        "relocation with google",
        "uscis address change",
        "cobalt – password expiration",
        "questionnaire has been assigned",
        "equity compensation",
        "recruitment",
        "interview",
        "job opportunity",
    ]
    if any(k in sender for k in work_senders) or any(
        k in subject for k in work_subjects
    ):
        return (
            "Work",
            "Professional recruitment, corporate relocation, immigration, career, or equity compensation",
        )

    # 6. Personal
    personal_senders = [
        "find my",
        "sutter",
        "urgent care",
        "dermatology",
        "nsudhanva@",
        "microsoft",
        "apple",
        "icloud",
        "doctor",
        "clinic",
        "kaiser",
        "quest diagnostics",
        "labcorp",
        "physical therapy",
        "challiance.org",
        "uidai.gov.in",
        "dmv",
        "maps timeline",
        "accounts.google.com",
        "search-noreply@google.com",
        "maanasanarayan",
        "anwarenterp",
    ]
    personal_subjects = [
        "appointment reminder",
        "visit summary",
        "test results",
        "a sound was played",
        "dmv appointment",
        "real id",
        "aadhaar",
        "security alert",
    ]
    if (
        any(k in sender for k in personal_senders)
        or ("via google maps" in sender)
        or any(k in subject for k in personal_subjects)
    ):
        return (
            "Personal",
            "Personal account, identity, health, device security, or direct personal communication",
        )

    # 7. Newsletters (Default)
    return "Newsletters", "Newsletter, digest, or marketing announcement"


def apply_classifications(token: str, decisions: dict | None = None) -> int:
    if decisions is None:
        if not OUTPUT_FILE.exists():
            print(
                f"Error: {OUTPUT_FILE} not found. Please provide classifications first."
            )
            sys.exit(1)
        decisions = json.loads(OUTPUT_FILE.read_text())
        print(f"Loaded {len(decisions)} classifications from {OUTPUT_FILE}")

    labels = get_labels(token)
    processed_label_id = ensure_label(token, "ai-processed", labels)

    cutoff_ts = (datetime.now(timezone.utc) - timedelta(days=90)).timestamp()

    # Group messages by (label_id, should_archive)
    groups: dict[tuple[str, bool], list[str]] = {}

    for mid, item in decisions.items():
        label_name = item.get("label", "Newsletters")
        lbl_id = ensure_label(token, label_name, labels)
        date_ts = item.get("date_ts", 0)
        archive = bool(date_ts and date_ts < cutoff_ts)
        key = (lbl_id, archive)
        groups.setdefault(key, []).append(mid)

    total_applied = 0
    total_archived = 0

    url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/batchModify"
    for (lbl_id, archive), ids in groups.items():
        # Gmail API allows up to 1000 IDs per batchModify call
        for chunk_start in range(0, len(ids), 1000):
            chunk_ids = ids[chunk_start : chunk_start + 1000]
            add_ids = [lbl_id, processed_label_id]
            remove_ids = ["INBOX"] if archive else []
            payload = json.dumps(
                {
                    "ids": chunk_ids,
                    "addLabelIds": add_ids,
                    "removeLabelIds": remove_ids,
                }
            ).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in (200, 204):
                    total_applied += len(chunk_ids)
                    if archive:
                        total_archived += len(chunk_ids)

    print(
        f"Successfully applied labels to {total_applied} emails ({total_archived} auto-archived >90d)."
    )
    OUTPUT_FILE.unlink(missing_ok=True)
    INPUT_FILE.unlink(missing_ok=True)
    return total_applied


def run_pipeline(token: str, batches: int = 10, batch_size: int = 500) -> None:
    grand_total = 0
    b = 0
    target_str = f"target: {batch_size}"
    while True:
        b += 1
        if batches > 0 and b > batches:
            break
        batches_str = f"{b}/{batches}" if batches > 0 else f"{b}/unlimited"
        token = get_token()
        print(f"\n--- Batch {batches_str} ({target_str}) ---", flush=True)
        items = fetch_batch(token, batch_size)
        if not items:
            print(
                "No more unprocessed items found! Reached end of inbox backlog.",
                flush=True,
            )
            break

        decisions = {}
        counts: dict[str, int] = {}
        for item in items:
            lbl, reason = classify_item(item)
            decisions[item["id"]] = {
                "label": lbl,
                "confidence": 0.95,
                "reason": reason,
                "date_ts": item.get("date_ts", 0),
            }
            counts[lbl] = counts.get(lbl, 0) + 1

        print(f"Batch {b} classifications: {counts}", flush=True)
        applied = apply_classifications(token, decisions)
        grand_total += applied
        print(f"Total processed in this session so far: {grand_total}", flush=True)

    print(f"\n=== Pipeline Completed: {grand_total} emails processed ===", flush=True)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    fetch_parser = sub.add_parser("fetch")
    fetch_parser.add_argument("--count", type=int, default=50)

    sub.add_parser("apply")

    run_parser = sub.add_parser("run")
    run_parser.add_argument(
        "--batches",
        type=int,
        default=0,
        help="Number of batches (0 for unlimited until drained)",
    )
    run_parser.add_argument("--batch-size", type=int, default=500)

    args = parser.parse_args()
    token = get_token()

    if args.cmd == "fetch":
        fetch_batch(token, args.count)
    elif args.cmd == "apply":
        apply_classifications(token)
    elif args.cmd == "run":
        run_pipeline(token, batches=args.batches, batch_size=args.batch_size)


if __name__ == "__main__":
    main()
