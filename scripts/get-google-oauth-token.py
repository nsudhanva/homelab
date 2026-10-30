#!/usr/bin/env python3
# /// script
# dependencies = [
#     "google-auth-oauthlib",
# ]
# ///
"""Interactive script to generate Google OAuth refresh token with Drive and Gmail scopes."""

import argparse
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]


def get_client_credentials() -> tuple[str, str]:
    """Read the OAuth client from GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or prompt."""
    client_id = (
        os.environ.get("GOOGLE_CLIENT_ID") or input("Enter Google Client ID: ").strip()
    )
    client_secret = (
        os.environ.get("GOOGLE_CLIENT_SECRET")
        or input("Enter Google Client Secret: ").strip()
    )
    return client_id, client_secret


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire Google Drive and Gmail OAuth tokens"
    )
    parser.add_argument(
        "--account",
        default="account",
        help="Account nickname from apps/accounts.yaml (e.g. personal, family)",
    )
    parser.add_argument(
        "--port", type=int, default=8080, help="Local redirect server port"
    )
    args = parser.parse_args()

    client_id, client_secret = get_client_credentials()
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
    print(
        f"\nStore credentials in Vault at the vault_path of '{args.account}' in apps/accounts.yaml:"
    )
    print(
        "kubectl -n vault exec -it vault-0 -- vault kv put kv/<vault_path> \\\n"
        f'  client_id="{client_id}" \\\n'
        f'  client_secret="{client_secret}" \\\n'
        f'  refresh_token="{creds.refresh_token}"\n'
    )


if __name__ == "__main__":
    main()
