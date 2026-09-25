#!/usr/bin/env bash
set -euo pipefail

FOLDER_ID="${BW_FOLDER_ID:-b4bcc38c-4296-41a4-b9b3-b4c50047ce37}"
URL="https://actual.sudhanva.me"
USERNAME="admin"
VAULT_AUTH_PATH="${VAULT_AUTH_PATH:-kv/actual}"
VAULT_SIMPLEFIN_PATH="${VAULT_SIMPLEFIN_PATH:-kv/actual-budget/simplefin}"

if [[ -z "${VAULT_TOKEN:-}" ]]; then
  echo "VAULT_TOKEN must be set" >&2
  exit 1
fi

vault_field() {
  kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
    vault kv get -field="$2" "$1"
}

PASSWORD="$(vault_field "$VAULT_AUTH_PATH" password)"
SIMPLEFIN_TOKEN="$(vault_field "$VAULT_SIMPLEFIN_PATH" setup_token)"

LOGIN_NAME="Actual Budget (Homelab)"
LOGIN_NOTES="Actual Budget personal finance on K3s cluster with SimpleFIN Bridge integration. Vault paths: ${VAULT_AUTH_PATH} and ${VAULT_SIMPLEFIN_PATH}"

NOTE_NAME="SimpleFIN Bridge Setup Token (Actual Budget)"
NOTE_CONTENT="Provider: https://beta-bridge.simplefin.org

Setup Token:
${SIMPLEFIN_TOKEN}

HashiCorp Vault Path:
${VAULT_SIMPLEFIN_PATH}"

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
