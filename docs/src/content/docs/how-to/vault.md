---
title: HashiCorp Vault Secrets Management
description: Deploy HashiCorp Vault to keep secrets in one location. Initialize and unseal Vault, configure External Secrets Operator, and sync secrets to Kubernetes workloads.
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

# Vault Secrets

Move the cluster secrets into Vault. Then use External Secrets Operator to sync them into Kubernetes.

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

Make sure that the pods are ready:

```bash
kubectl -n vault get pods
kubectl -n external-secrets get pods
```

If Vault is Pending, make sure that the PVC is bound to local-path storage:

```bash
kubectl -n vault get pvc
```

## Step 2: Initialize and unseal Vault

Keep the unseal keys and the root token offline, for example in a password manager. If you lose them, the only recovery is to wipe the Vault PVC and initialize Vault again. This deletes all stored secrets.

Initialize Vault. The `vault operator init` command prints five unseal keys with a threshold of three. Save the unseal keys and the root token in a safe location.

```bash
kubectl -n vault exec -it vault-0 -- vault operator init
```

Unseal Vault with the necessary number of keys:

```bash
kubectl -n vault exec -it vault-0 -- vault operator unseal
```

Log in with the root token:

```bash
kubectl -n vault exec -it vault-0 -- vault login
```

## Step 3: Enable the KV v2 secrets engine

Enable KV v2 at `kv/`. This path agrees with the ExternalSecret store configuration:

```bash
kubectl -n vault exec -it vault-0 -- vault secrets enable -path=kv kv-v2
```

## Step 4: Create secrets in Vault

Write the secrets that Kubernetes uses now:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/external-dns/cloudflare api-token="REPLACE_ME"
kubectl -n vault exec -it vault-0 -- vault kv put kv/cert-manager/cloudflare api-token="REPLACE_ME"
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/operator-oauth client_id="REPLACE_ME" client_secret="REPLACE_ME"
```

### Step 4a: Filebrowser credentials

Make a bcrypt hash of the password:

```bash
htpasswd -bnBC 12 filebrowser "REPLACE_ME" | cut -d ':' -f2
```

Store the username, plaintext password, and bcrypt hash:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/filebrowser/auth \
  username="filebrowser" \
  password="REPLACE_ME" \
  password_hash="REPLACE_ME"
```

## ArgoCD Image Updater credentials

Store registry and Git credentials for ArgoCD Image Updater:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/ghcr \
  username="REPLACE_ME" token="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd-image-updater/dockerhub \
  username="REPLACE_ME" token="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/argocd/repo-creds \
  username="REPLACE_ME" token="REPLACE_ME"
```

## Step 5: Create a token for External Secrets Operator

Create a minimal policy and a token that can read from `kv/`:

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

## Step 6: Add new secrets and ExternalSecret resources

To add a new secret, write it to Vault first. Then create an ExternalSecret manifest in the same folder as the workload that uses the secret.

Example Vault write:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/my-app/api token="REPLACE_ME"
```

Example ExternalSecret. Save it as a separate YAML file, for example `apps/my-app/externalsecret.yaml` or `infrastructure/<component>/external-secret.yaml`:

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

Make sure that External Secrets Operator created or updated the target secrets:

```bash
kubectl -n external-dns get secret cloudflare-api-token
kubectl -n cert-manager get secret cloudflare-api-token
kubectl -n tailscale get secret operator-oauth
```

When the secrets agree with Vault, remove all secrets that you created manually. External Secrets Operator then owns the secrets.

## Step 8: Access the Vault UI

Vault is available at `https://vault.sudhanva.me` through the Tailscale Gateway.

## Troubleshooting

### Vault UI blank page

Large UI bundles can time out through the Gateway. If the Vault UI shows a blank page in the browser but `curl` works, examine the Envoy Gateway logs. Look for `response_timeout` entries on `/ui/assets/...`.

Update the Vault HTTPRoute to increase the request timeout:

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

Commit the change. ArgoCD syncs `infrastructure/gateway/vault-httproute.yaml`.

### ClusterSecretStore not ready

If `infra-external-secrets` is Degraded or ExternalSecrets show `SecretSyncedError`, examine the Vault token secret:

```bash
kubectl -n external-secrets get secret vault-eso-token
kubectl -n external-secrets get clustersecretstore vault -o yaml
```

The ClusterSecretStore becomes Ready only when `vault-eso-token` exists and contains a valid token.

### ExternalSecrets still failing after Vault recovery

If you initialized Vault again, or added secrets after External Secrets failed, force a resync.

Step 1: Request a reconcile for all ExternalSecrets.

```bash
kubectl get externalsecrets -A -o jsonpath='{range .items[*]}{.metadata.namespace}{" "}{.metadata.name}{"\n"}{end}' | while read -r ns name; do
  kubectl -n "$ns" annotate externalsecret "$name" reconcile.external-secrets.io/requested-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" --overwrite
done
```

Step 2: Examine the sync status.

```bash
kubectl get externalsecrets -A
```
