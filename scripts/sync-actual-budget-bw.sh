#!/usr/bin/env bash
set -euo pipefail

FOLDER_ID="b4bcc38c-4296-41a4-b9b3-b4c50047ce37"
URL="https://actual.sudhanva.me"
USERNAME="admin"
PASSWORD="REDACTED"

LOGIN_NAME="Actual Budget (Homelab)"
LOGIN_NOTES="Actual Budget personal finance on K3s cluster. Auto-bootstrapped with SimpleFIN Bridge integration (15 accounts linked). Vault Paths: kv/actual-budget/auth and kv/actual-budget/simplefin"

NOTE_NAME="SimpleFIN Bridge Setup Token (Actual Budget)"
NOTE_CONTENT="Provider: https://beta-bridge.simplefin.org
Status: Claimed & Active in Actual Budget Server

Setup Token:
REDACTED

Claim URL (Decoded):
https://beta-bridge.simplefin.org/simplefin/claim/REDACTED

Linked Financial Institutions & Accounts (21 total):
- [Sudhanva] Chase Bank: Chase Total Checking, Chase Amazon Prime Visa
- [Sudhanva] American Express: Amex HYSA, Amex Gold Card
- [Sudhanva] Santander Bank: Santander Checking, Santander Savings
- [Sudhanva] Apple Card
- [Sudhanva] Robinhood: Credit Card, Individual, Individual, Roth IRA, Crypto, Checking, Savings
- [Joint] Robinhood: Robinhood Joint
- [Maanasa] Chase Bank: Chase Sapphire Reserve, Chase Freedom Flex
- [Maanasa] Discover Bank: Discover Online Savings, Discover Cashback Debit, Discover it Card
- [Maanasa] Apple Card

HashiCorp Vault Path:
kv/actual-budget/simplefin"

if [[ -z "${BW_SESSION:-}" ]]; then
  echo "Unlocking Bitwarden CLI..."
  BW_SESSION="$(bw unlock --raw)"
  export BW_SESSION
fi

echo "Syncing Bitwarden vault..."
bw sync --session "$BW_SESSION"

echo "Creating Bitwarden login item for Actual Budget..."
ITEM_JSON=$(bw --session "$BW_SESSION" get template item | jq \
  --arg name "$LOGIN_NAME" \
  --arg url "$URL" \
  --arg username "$USERNAME" \
  --arg password "$PASSWORD" \
  --arg notes "$LOGIN_NOTES" \
  --arg folderId "$FOLDER_ID" \
  '.name = $name |
   .type = 1 |
   .folderId = $folderId |
   .login.username = $username |
   .login.password = $password |
   .login.uris = [{uri: $url, match: null}] |
   .notes = $notes')

echo "$ITEM_JSON" | bw encode | bw --session "$BW_SESSION" create item > /dev/null
echo "✓ Successfully created: $LOGIN_NAME"

echo "Creating Bitwarden secure note for SimpleFIN setup token..."
NOTE_JSON=$(bw --session "$BW_SESSION" get template item | jq \
  --arg name "$NOTE_NAME" \
  --arg notes "$NOTE_CONTENT" \
  --arg folderId "$FOLDER_ID" \
  '.name = $name |
   .type = 2 |
   .folderId = $folderId |
   .secureNote.type = 0 |
   .notes = $notes')

echo "$NOTE_JSON" | bw encode | bw --session "$BW_SESSION" create item > /dev/null
echo "✓ Successfully created: $NOTE_NAME"

bw sync --session "$BW_SESSION"
echo "All credentials and secure notes successfully synced to Bitwarden!"
