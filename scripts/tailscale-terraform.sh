#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/tailscale-terraform.sh <command> [args]

Runs Terraform in terraform/tailscale with credentials read from Vault.

Commands:
  init             Initialize the R2 backend
  plan|apply|...   Any other Terraform command, passed through
  github-secrets   Copy the Vault credentials into the GitHub Actions secrets

Environment:
  VAULT_TOKEN                 Required. A Vault token that can read the paths below
  VAULT_TAILSCALE_TF_PATH     Default kv/tailscale/terraform (client_id, client_secret)
  VAULT_TF_STATE_PATH         Default kv/terraform/state (access_key_id, secret_access_key, endpoint)
EOF
}

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAILSCALE_PATH="${VAULT_TAILSCALE_TF_PATH:-kv/tailscale/terraform}"
STATE_PATH="${VAULT_TF_STATE_PATH:-kv/terraform/state}"

if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${VAULT_TOKEN:-}" ]]; then
  echo "VAULT_TOKEN must be set" >&2
  exit 1
fi

vault_field() {
  kubectl -n vault exec -i vault-0 -- env VAULT_TOKEN="$VAULT_TOKEN" \
    vault kv get -field="$2" "$1"
}

TAILSCALE_OAUTH_CLIENT_ID="$(vault_field "$TAILSCALE_PATH" client_id)"
TAILSCALE_OAUTH_CLIENT_SECRET="$(vault_field "$TAILSCALE_PATH" client_secret)"
AWS_ACCESS_KEY_ID="$(vault_field "$STATE_PATH" access_key_id)"
AWS_SECRET_ACCESS_KEY="$(vault_field "$STATE_PATH" secret_access_key)"
R2_ENDPOINT="$(vault_field "$STATE_PATH" endpoint)"
export TAILSCALE_OAUTH_CLIENT_ID TAILSCALE_OAUTH_CLIENT_SECRET AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY

case "$1" in
  init)
    shift
    terraform -chdir="$ROOT/terraform/tailscale" init \
      -backend-config="endpoints={s3=\"${R2_ENDPOINT}\"}" "$@"
    ;;
  github-secrets)
    printf '%s' "$TAILSCALE_OAUTH_CLIENT_ID" | gh secret set TAILSCALE_TF_OAUTH_CLIENT_ID
    printf '%s' "$TAILSCALE_OAUTH_CLIENT_SECRET" | gh secret set TAILSCALE_TF_OAUTH_CLIENT_SECRET
    printf '%s' "$AWS_ACCESS_KEY_ID" | gh secret set TF_STATE_R2_ACCESS_KEY_ID
    printf '%s' "$AWS_SECRET_ACCESS_KEY" | gh secret set TF_STATE_R2_SECRET_ACCESS_KEY
    printf '%s' "$R2_ENDPOINT" | gh secret set TF_STATE_R2_ENDPOINT
    echo "Updated 5 GitHub Actions secrets from Vault."
    ;;
  *)
    terraform -chdir="$ROOT/terraform/tailscale" "$@"
    ;;
esac
