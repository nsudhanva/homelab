---
title: HashiCorp Vault Secrets Management
description: Deploy HashiCorp Vault, initialize and unseal it, configure External Secrets Operator, and sync the secrets to Kubernetes workloads.
keywords:
  - hashicorp vault kubernetes
  - vault secrets management
  - external secrets operator
  - kubernetes secrets
  - vault kv secrets
  - clustersecretstore
  - vault initialization
  - vault unseal
sidebar:
  order: 8
---

Vault keeps all cluster secrets. External Secrets Operator syncs them into Kubernetes Secrets.

```mermaid
flowchart LR
  Vault["Vault kv/"] --> ESO["External Secrets Operator"]
  ESO --> Secret["Kubernetes Secret"]
  Secret --> Workload["Apps and controllers"]
```

## Detailed Secret Sync Path

```mermaid
flowchart TB
  Vault["Vault KV v2 (kv/)"] --> Store["ClusterSecretStore"]
  Store --> ESO["External Secrets Operator"]
  ESO --> ExternalSecret["ExternalSecret"]
  ExternalSecret --> Target["Target Secret"]
  Target --> Consumers["Deployments/Controllers"]
```

## Step 1: Deploy Vault and External Secrets Operator

Push the repository changes. ArgoCD syncs `infrastructure/vault/` and `infrastructure/external-secrets/`.

Verify that the pods are ready:

```bash
kubectl -n vault get pods
kubectl -n external-secrets get pods
```

If Vault is Pending, verify that the PVC binds to local-path storage:

```bash
kubectl -n vault get pvc
```

## Step 2: Initialize and unseal Vault

Keep the unseal keys and the root token offline, for example in a password manager. If you lose them, you must delete the data on the Vault PVC and initialize Vault again. This deletes all stored secrets.

Initialize Vault. The `vault operator init` command prints five unseal keys with a threshold of three. Save the unseal keys and the root token in a safe location.

```bash
kubectl -n vault exec -it vault-0 -- vault operator init
```

Unseal Vault with three of the five keys. Run this command one time for each key:

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal
```

Log in with the root token:

```bash
kubectl -n vault exec -it vault-0 -- vault login
```

## Step 3: Enable the KV v2 secrets engine

Enable KV v2 at `kv/`. The ClusterSecretStore reads from this path.

```bash
kubectl -n vault exec -it vault-0 -- vault secrets enable -path=kv kv-v2
```

## Step 4: Create secrets in Vault

Write the secrets for ExternalDNS, cert-manager, and the Tailscale Operator:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/external-dns/cloudflare api-token="REPLACE_ME"
kubectl -n vault exec -it vault-0 -- vault kv put kv/cert-manager/cloudflare api-token="REPLACE_ME"
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/operator-oauth client_id="REPLACE_ME" client_secret="REPLACE_ME"
```

### Step 4a: Filebrowser credentials

Generate a bcrypt hash of the password:

```bash
htpasswd -bnBC 12 filebrowser "REPLACE_ME" | cut -d ':' -f2
```

Store the username, the plaintext password, and the bcrypt hash:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/filebrowser/auth \
  username="filebrowser" \
  password="REPLACE_ME" \
  password_hash="REPLACE_ME"
```

### Step 4b: ArgoCD Image Updater credentials

Store the registry and Git credentials for ArgoCD Image Updater:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/ghcr \
  username="REPLACE_ME" token="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd/repo-creds \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 5: Configure Kubernetes auth for External Secrets Operator

External Secrets Operator logs in to Vault with its own ServiceAccount. Vault issues a short-lived token for each login. There is no static token.

Write a read-only policy for `kv/`:

```bash
kubectl -n vault exec -it vault-0 -- /bin/sh -c 'cat > /tmp/eso-policy.hcl <<EOF
path "kv/data/*" {
  capabilities = ["read"]
}
path "kv/metadata/*" {
  capabilities = ["read", "list"]
}
EOF'
kubectl -n vault exec -it vault-0 -- vault policy write eso-policy /tmp/eso-policy.hcl
```

Enable the Kubernetes auth method. Vault runs in the cluster, so it uses its own ServiceAccount and CA to review tokens.

```bash
kubectl -n vault exec -it vault-0 -- vault auth enable kubernetes
kubectl -n vault exec -it vault-0 -- vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc:443"
```

Bind the `external-secrets` ServiceAccount to the policy. The role accepts only tokens with the `vault` audience.

```bash
kubectl -n vault exec -it vault-0 -- vault write auth/kubernetes/role/external-secrets \
  bound_service_account_names=external-secrets \
  bound_service_account_namespaces=external-secrets \
  policies=eso-policy \
  audience=vault \
  ttl=1h
```

The ClusterSecretStore `vault` in `infrastructure/external-secrets/clustersecretstore.yaml` uses this role. ArgoCD syncs the ClusterSecretStore.

## Step 6: Add new secrets and ExternalSecret resources

To add a new secret, write it to Vault first. Then create an ExternalSecret manifest in the same folder as the workload that uses the secret.

Example Vault write:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/my-app/api token="REPLACE_ME"
```

Example ExternalSecret manifest. Save it as a separate YAML file, for example `apps/my-app/externalsecret.yaml` or `infrastructure/<component>/external-secret.yaml`.

```yaml
apiVersion: external-secrets.io/v1
kind: ExternalSecret
metadata:
  name: my-app-api
  namespace: my-app
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: vault
    kind: ClusterSecretStore
  target:
    name: my-app-api
    creationPolicy: Owner
  data:
  - secretKey: token
    remoteRef:
      key: my-app/api
      property: token
```

Commit the new manifest. ArgoCD syncs it.

## Step 7: Validate ExternalSecret sync

Make sure that External Secrets Operator created or updated the target Secrets:

```bash
kubectl -n external-dns get secret cloudflare-api-token
kubectl -n cert-manager get secret cloudflare-api-token
kubectl -n tailscale get secret operator-oauth
```

Every Secret that comes from Vault has `creationPolicy: Owner`, so External Secrets Operator owns it. Do not create or edit these Secrets with `kubectl`.

## Vault paths and the ExternalSecrets that read them

This table lists every ExternalSecret in the repository. All paths are under the KV v2 mount `kv/`. The `homelab-ai-credentials` ExternalSecret comes from the kustomize Component `packages/homelab-ai/kustomize/`. Each app that includes the Component gets its own copy in its namespace.

| Vault path | Properties read | ExternalSecret (namespace/name) | Manifest |
| --- | --- | --- | --- |
| `kv/argocd-image-updater/ghcr` | `username`, `token` | `argocd/argocd-image-updater-registries` | `infrastructure/external-secrets/external-secret-argocd-image-updater-registries.yaml` |
| `kv/argocd/repo-creds` | `username`, `token` | `argocd/repo-homelab` | `infrastructure/external-secrets/external-secret-argocd-repo-creds.yaml` |
| `kv/cert-manager/cloudflare` | `api-token` | `cert-manager/cloudflare-api-token` | `infrastructure/external-secrets/external-secret-cloudflare-cert-manager.yaml` |
| `kv/cert-manager/cloudflare` | `api-token` | `tailscale/cloudflare-api-token` | `infrastructure/external-secrets/external-secret-cloudflare-cert-manager-tailscale.yaml` |
| `kv/external-dns/cloudflare` | `api-token` | `external-dns/cloudflare-api-token` | `infrastructure/external-secrets/external-secret-cloudflare-external-dns.yaml` |
| `kv/tailscale/operator-oauth` | `client_id`, `client_secret` | `tailscale/operator-oauth` | `infrastructure/external-secrets/external-secret-tailscale-operator.yaml` |
| `kv/monitoring/grafana-admin` | `admin-user`, `admin-password` | `monitoring/grafana-admin` | `infrastructure/prometheus/external-secret-grafana.yaml` |
| `kv/telegram/bot` | `token`, `chat_id` | `monitoring/alertmanager-telegram` | `infrastructure/prometheus/external-secret-telegram.yaml` |
| `kv/telegram/bot` | `token` | `gmail-classifier/gmail-credentials-personal`, `gmail-classifier/gmail-credentials-family` | `apps/gmail-classifier/secret-personal.yaml`, `apps/gmail-classifier/secret-family.yaml` |
| `kv/telegram/bot` | `token` | `drive-organizer/drive-credentials-personal`, `drive-organizer/drive-credentials-family` | `apps/drive-organizer/secret-personal.yaml`, `apps/drive-organizer/secret-family.yaml` |
| `kv/gmail/credentials` | `client_id`, `client_secret`, `refresh_token` | `gmail-classifier/gmail-credentials-personal` | `apps/gmail-classifier/secret-personal.yaml` |
| `kv/gmail/credentials` | `client_id`, `client_secret`, `refresh_token` | `drive-organizer/drive-credentials-personal` | `apps/drive-organizer/secret-personal.yaml` |
| `kv/google/accounts/family` | `client_id`, `client_secret`, `refresh_token` | `gmail-classifier/gmail-credentials-family` | `apps/gmail-classifier/secret-family.yaml` |
| `kv/google/accounts/family` | `client_id`, `client_secret`, `refresh_token` | `drive-organizer/drive-credentials-family` | `apps/drive-organizer/secret-family.yaml` |
| `kv/actual` | `password` | `actual-classifier/actual-classifier-secrets` | `apps/actual-classifier/secret.yaml` |
| `kv/filebrowser/auth` | `username`, `password_hash` | `media/filebrowser-auth` | `apps/filebrowser/external-secret-auth.yaml` |
| `kv/qbittorrent/vpn` | `private_key`, `public_key`, `endpoint_ip`, `endpoint_port`, `addresses` | `media/qbittorrent-vpn` | `apps/qbittorrent/external-secret-vpn.yaml` |
| `kv/technitium/admin` | `admin-user`, `admin-password` | `technitium/technitium-admin` | `apps/technitium/external-secret.yaml` |
| `kv/sarvam` | `api_key` | `home-assistant/sarvam-api` | `apps/home-assistant/external-secret-sarvam.yaml` |
| `kv/openrouter` | `api_key` | `<namespace>/homelab-ai-credentials` in `actual-classifier`, `monitoring`, `drive-organizer`, and `gmail-classifier` | `packages/homelab-ai/kustomize/externalsecret.yaml` |
| `kv/anthropic` | `api_key`, `workspace_id` | `<namespace>/homelab-ai-credentials` in `actual-classifier`, `monitoring`, `drive-organizer`, and `gmail-classifier` | `packages/homelab-ai/kustomize/externalsecret.yaml` |

Terraform also reads two paths. No ExternalSecret syncs them into the cluster. The script `scripts/tailscale-terraform.sh` reads them at run time and copies them to GitHub Actions secrets.

| Vault path | Properties | Used by |
| --- | --- | --- |
| `kv/tailscale/terraform` | `client_id`, `client_secret` | `terraform/tailscale/` (Tailscale OAuth client) |
| `kv/terraform/state` | `access_key_id`, `secret_access_key`, `endpoint` | Terraform state in the R2 bucket `homelab-terraform-state` |

Vault also holds values that no manifest reads. Examples are the plaintext `password` property in `kv/filebrowser/auth` and the logins for the media apps. The cluster does not use these values. To find the readers of a path, search the repository:

```bash
git grep -n "key: <path>" -- apps infrastructure packages
```

## Step 8: Access the Vault UI

Vault is available at `https://vault.sudhanva.me` through the Tailscale Gateway.

## Step 9: Back Up Secrets to Bitwarden

Back up all cluster secrets and Vault keys to Bitwarden for disaster recovery.

- Store all entries in the Bitwarden `Homelab` folder (`b4bcc38c-4296-41a4-b9b3-b4c50047ce37`).
- Use the name format `Homelab - <Component> <Role>`.
- Add the custom field `tag: homelab` to every entry.

### Required Bitwarden Backup Items

| Item | Contents |
| --- | --- |
| `Homelab - HashiCorp Vault Master Keys` | The five unseal keys, the unseal threshold (3), and the root token |
| `Homelab - HashiCorp Vault Keys Raw JSON Backup` | The raw JSON response from `vault operator init` |
| `Homelab - ArgoCD Admin` | The ArgoCD admin password |
| `Homelab - ArgoCD GitHub & GHCR Token` | The GitHub personal access token for the Git repository and the container registry |
| `Homelab - Cloudflare API Token` | The DNS-01 API token for cert-manager and ExternalDNS |
| `Homelab - Tailscale Operator OAuth` | The Tailscale Operator OAuth client ID and secret |
| `Homelab - qBittorrent WireGuard VPN` | The WireGuard private key, public key, and endpoint parameters |

Run this command with the Bitwarden CLI to list the items in the folder:

```bash
bw list items --folderid b4bcc38c-4296-41a4-b9b3-b4c50047ce37
```

## Troubleshooting

### Vault UI blank page

Large UI bundles can time out through the Gateway. If the Vault UI shows a blank page in the browser but `curl` works, examine the Envoy Gateway logs. Look for `response_timeout` entries on `/ui/assets/...`.

The Vault HTTPRoute in `infrastructure/gateway/vault-httproute.yaml` sets these timeouts. If the errors continue, increase the values:

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: vault
  namespace: vault
spec:
  rules:
  - timeouts:
      request: 60s
      backendRequest: 60s
```

Commit the change. ArgoCD syncs the HTTPRoute.

### ClusterSecretStore not ready

If `infra-external-secrets` is Degraded or ExternalSecrets show `SecretSyncedError`, examine the ClusterSecretStore and the Kubernetes auth role:

```bash
kubectl -n external-secrets get clustersecretstore vault -o yaml
kubectl -n vault exec -it vault-0 -- vault read auth/kubernetes/role/external-secrets
kubectl -n external-secrets logs deploy/external-secrets | grep -i vault
```

The ClusterSecretStore becomes Ready only when Vault is unsealed and the `external-secrets` role exists.

### ExternalSecrets fail after Vault recovery

If you initialize Vault again, or add secrets after an ExternalSecret fails, force a resync.

Step 1: Request a reconcile for all ExternalSecrets:

```bash
kubectl get externalsecrets -A -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.name}{"\n"}{end}' | while read -r ns name; do
  kubectl -n "$ns" annotate externalsecret "$name" reconcile.external-secrets.io/requested-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" --overwrite
done
```

Step 2: Examine the sync status:

```bash
kubectl get externalsecrets -A
```
