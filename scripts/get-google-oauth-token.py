#!/usr/bin/env python3
"""Interactive script to generate Google OAuth refresh token with Drive and Gmail scopes."""

import argparse
import subprocess
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/drive",
]


def get_client_credentials(kubeconfig: str) -> tuple[str, str]:
    try:
        id_cmd = [
            "kubectl",
            "--kubeconfig",
            kubeconfig,
            "-n",
            "drive-organizer",
            "get",
            "secret",
            "drive-credentials",
            "-o",
            "jsonpath={.data.DRIVE_CLIENT_ID}",
        ]
        cid_b64 = subprocess.check_output(id_cmd, text=True).strip()

        secret_cmd = [
            "kubectl",
            "--kubeconfig",
            kubeconfig,
            "-n",
            "drive-organizer",
            "get",
            "secret",
            "drive-credentials",
            "-o",
            "jsonpath={.data.DRIVE_CLIENT_SECRET}",
        ]
        csec_b64 = subprocess.check_output(secret_cmd, text=True).strip()

        import base64

        client_id = base64.b64decode(cid_b64).decode("utf-8")
        client_secret = base64.b64decode(csec_b64).decode("utf-8")
        return client_id, client_secret
    except (subprocess.SubprocessError, KeyError, ValueError, Exception) as e:  # noqa: BLE001
        print(f"Failed to fetch credentials from cluster: {e}", file=sys.stderr)
        client_id = input("Enter Google Client ID: ").strip()
        client_secret = input("Enter Google Client Secret: ").strip()
        return client_id, client_secret


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Acquire Google Drive and Gmail OAuth tokens"
    )
    parser.add_argument(
        "--kubeconfig", default="k3s.kubeconfig", help="Path to k3s.kubeconfig"
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
    print(f"Requested Scopes: {', '.join(SCOPES)}\n")
    creds = flow.run_local_server(
        port=args.port, prompt="consent", access_type="offline"
    )

    print("\nAuthentication successful!")
    print(f"Refresh Token: {creds.refresh_token}")
    print("\nUpdate Vault with the new refresh token:")
    print(
        'kubectl -n vault exec -it vault-0 -- vault kv patch kv/gmail/credentials refresh_token="<YOUR_NEW_REFRESH_TOKEN>"'
    )


if __name__ == "__main__":
    main()
