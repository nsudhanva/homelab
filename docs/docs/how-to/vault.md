---
sidebar_position: 9
title: Vault Secrets
---

# Vault Secrets

Move cluster secrets into Vault and sync them into Kubernetes with External Secrets Operator.

## Step 1: Deploy Vault and External Secrets Operator

Push the repo changes and let ArgoCD sync `infrastructure/vault/` and `infrastructure/external-secrets/`.

Confirm the pods are ready:

```bash
kubectl -n vault get pods
kubectl -n external-secrets get pods
```

## Step 2: Initialize and unseal Vault

Initialize Vault and save the unseal keys and root token somewhere safe.

```bash
kubectl -n vault exec -it vault-0 -- vault operator init
```

Unseal Vault with the required number of keys:

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal
```

Log in with the root token:

```bash
kubectl -n vault exec -it vault-0 -- vault login
```

## Step 3: Enable the KV v2 secrets engine

Enable KV v2 at `kv/` to match the ExternalSecret store config:

```bash
kubectl -n vault exec -it vault-0 -- vault secrets enable -path=kv kv-v2
```

## Step 4: Create secrets in Vault

Write the secrets that Kubernetes currently expects:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/external-dns/cloudflare api-token="REPLACE_ME"
kubectl -n vault exec -it vault-0 -- vault kv put kv/cert-manager/cloudflare api-token="REPLACE_ME"
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/operator-oauth client_id="REPLACE_ME" client_secret="REPLACE_ME"
```

## Step 5: Create a token for External Secrets Operator

Create a minimal policy and a token that can read from `kv/`.

```bash
kubectl -n vault exec -it vault-0 -- /bin/sh -c 'cat > /tmp/external-secrets.hcl <<EOF
path "kv/data/*" {
  capabilities = ["read"]
}
path "kv/metadata/*" {
  capabilities = ["read"]
}
EOF'
kubectl -n vault exec -it vault-0 -- vault policy write external-secrets /tmp/external-secrets.hcl
kubectl -n vault exec -it vault-0 -- vault token create -policy=external-secrets
```

Store the token in Kubernetes:

```bash
kubectl -n external-secrets create secret generic vault-eso-token --from-literal=token="REPLACE_ME"
```

## Step 6: Validate ExternalSecret sync

Check that External Secrets Operator created or updated the target secrets:

```bash
kubectl -n external-dns get secret cloudflare-api-token
kubectl -n cert-manager get secret cloudflare-api-token
kubectl -n tailscale get secret operator-oauth
```

Once the secrets match Vault, remove any manually created secrets so External Secrets Operator owns them.

## Step 7: Access the Vault UI

Vault is exposed at `https://vault.sudhanva.me` via the Tailscale Gateway.
