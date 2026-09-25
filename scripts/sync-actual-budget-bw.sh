#!/usr/bin/env bash
set -euo pipefail

FOLDER_ID="b4bcc38c-4296-41a4-b9b3-b4c50047ce37"
NAME="Actual Budget (Homelab)"
URL="https://actual.sudhanva.me"
USERNAME="admin"
PASSWORD="REDACTED"
NOTES="Actual Budget personal finance on K3s cluster. Auto-bootstrapped with SimpleFIN Bridge integration (7 accounts linked). Vault Paths: kv/actual-budget/auth and kv/actual-budget/simplefin"

if [[ -z "${BW_SESSION:-}" ]]; then
  echo "Unlocking Bitwarden CLI..."
  BW_SESSION="$(bw unlock --raw)"
  export BW_SESSION
fi

echo "Syncing Bitwarden vault..."
bw sync --session "$BW_SESSION"

echo "Creating Bitwarden login item for Actual Budget..."
ITEM_JSON=$(bw --session "$BW_SESSION" get template item | jq \
  --arg name "$NAME" \
  --arg url "$URL" \
  --arg username "$USERNAME" \
  --arg password "$PASSWORD" \
  --arg notes "$NOTES" \
  --arg folderId "$FOLDER_ID" \
  '.name = $name |
   .type = 1 |
   .folderId = $folderId |
   .login.username = $username |
   .login.password = $password |
   .login.uris = [{uri: $url, match: null}] |
   .notes = $notes')

echo "$ITEM_JSON" | bw encode | bw --session "$BW_SESSION" create item > /dev/null
bw sync --session "$BW_SESSION"
echo "Successfully created and synced: $NAME in Bitwarden!"
