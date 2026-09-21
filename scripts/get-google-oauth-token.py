#!/usr/bin/env python3
# /// script
# dependencies = [
#     "google-auth-oauthlib",
# ]
# ///
"""Interactive script to generate Google OAuth refresh token with Drive and Gmail scopes."""

import argparse
import subprocess
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]


def get_client_credentials(kubeconfig: str | None = None) -> tuple[str, str]:
    base_cmd = ["kubectl"]
    if kubeconfig:
        base_cmd.extend(["--kubeconfig", kubeconfig])

    for secret_name in (
        "drive-credentials-primary",
        "drive-credentials",
        "gmail-credentials-primary",
        "gmail-credentials",
    ):
        try:
            id_cmd = base_cmd + [
                "-n",
                "drive-organizer",
                "get",
                "secret",
                secret_name,
                "-o",
                "jsonpath={.data.DRIVE_CLIENT_ID}",
            ]
            cid_b64 = subprocess.check_output(
                id_cmd, text=True, stderr=subprocess.DEVNULL
            ).strip()

            secret_cmd = base_cmd + [
                "-n",
                "drive-organizer",
                "get",
                "secret",
                secret_name,
                "-o",
                "jsonpath={.data.DRIVE_CLIENT_SECRET}",
            ]
            csec_b64 = subprocess.check_output(
                secret_cmd, text=True, stderr=subprocess.DEVNULL
            ).strip()

            import base64

            if cid_b64 and csec_b64:
                client_id = base64.b64decode(cid_b64).decode("utf-8")
                client_secret = base64.b64decode(csec_b64).decode("utf-8")
                return client_id, client_secret
        except (subprocess.SubprocessError, KeyError, ValueError, Exception):  # noqa: BLE001, S112
            continue

    client_id = input("Enter Google Client ID: ").strip()
    client_secret = input("Enter Google Client Secret: ").strip()
    return client_id, client_secret


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire Google Drive and Gmail OAuth tokens"
    )
    parser.add_argument(
        "--account",
        default="account",
        help="Account nickname (e.g. personal, work, family)",
    )
    parser.add_argument(
        "--kubeconfig", default=None, help="Path to optional kubeconfig"
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Local redirect server port"
    )
    args = parser.parse_args()

    client_id, client_secret = get_client_credentials(args.kubeconfig)
    if not client_id or not client_secret:
        print("Missing client_id or client_secret.", file=sys.stderr)
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [
                f"http://localhost:{args.port}/",
                "http://localhost",
            ],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    print("\nStarting local OAuth authentication flow...")
    print(f"Target Account: {args.account}")
    print(f"Requested Scopes: {', '.join(SCOPES)}\n")
    creds = flow.run_local_server(
        port=args.port, prompt="consent", access_type="offline"
    )

    print("\nAuthentication successful!")
    print(f"Refresh Token: {creds.refresh_token}")
    print(f"\nStore credentials in Vault for account '{args.account}':")
    print(
        f"kubectl -n vault exec -it vault-0 -- vault kv put kv/google/accounts/{args.account} \\\n"
        f'  client_id="{client_id}" \\\n'
        f'  client_secret="{client_secret}" \\\n'
        f'  refresh_token="{creds.refresh_token}"\n'
    )


if __name__ == "__main__":
    main()
