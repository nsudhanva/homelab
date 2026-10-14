---
title: Deploy Headlamp Kubernetes Dashboard
description: Deploy Headlamp as a Kubernetes dashboard with Tailscale Gateway ingress. Configure OIDC authentication with Vault and collect metrics with Prometheus.
keywords:
  - headlamp kubernetes
  - kubernetes dashboard
  - headlamp oidc
  - vault oidc kubernetes
  - kubernetes ui
  - headlamp metrics
  - tailscale gateway headlamp
sidebar:
  order: 17
---

# Expose Headlamp With Tailscale Gateway

This guide shows how to deploy the Headlamp UI. The Tailscale Gateway API exposes it at `headlamp.sudhanva.me`.

## Step 1: Add the Headlamp app manifests

Create a new app directory under `apps/`. Use a separate manifest for each resource.

The layout is as follows:

- `apps/headlamp/app.yaml`
- `apps/headlamp/namespace.yaml`
- `apps/headlamp/serviceaccount.yaml`
- `apps/headlamp/clusterrolebinding.yaml`
- `apps/headlamp/secret-token.yaml`
- `apps/headlamp/deployment.yaml`
- `apps/headlamp/service.yaml`
- `apps/headlamp/servicemonitor.yaml`
- `apps/headlamp/httproute.yaml`

The `app.yaml` file defines the app name, the path, and the namespace.

```yaml
name: headlamp
path: apps/headlamp
namespace: headlamp
```

Expose the service with an `HTTPRoute` that points to the Tailscale Gateway.

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: headlamp
  namespace: headlamp
  annotations:
    argocd.argoproj.io/sync-options: SkipDryRunOnMissingResource=true
spec:
  parentRefs:
  - name: tailscale-gateway
    namespace: tailscale
    sectionName: https
  hostnames:
  - headlamp.sudhanva.me
  rules:
  - backendRefs:
    - name: headlamp
      port: 80
```

## Step 2: Commit and push

ArgoCD monitors the repo and applies the changes through ApplicationSets.

```bash
git add apps/headlamp
git commit -m "Add headlamp app"
git push
```

## Step 3: Access Headlamp

Open `https://headlamp.sudhanva.me` in your browser. Headlamp runs with `-unsafe-use-service-account-token`. It signs in automatically with the in-cluster service account credentials, which have `cluster-admin` privileges.

If you want a short-lived token, make one manually:

```bash
kubectl -n headlamp create token headlamp
```

## Step 4: Cluster role permissions

The file `apps/headlamp/clusterrolebinding.yaml` binds the Headlamp service account directly to `cluster-admin`. This gives administrative control. If you want read-only access, change the `roleRef` to the built-in `view` ClusterRole.

## OIDC Login With Vault

This procedure replaces short-lived service account tokens with long-lived OIDC logins. Vault is the identity provider. The Kubernetes API server must trust Vault as an OIDC issuer.

### Step 1: Create Vault OIDC key, provider, and client

Log in to Vault with an admin token.

```bash
kubectl -n vault exec -it vault-0 -- vault login
```

Create a signing key and a provider.

```bash
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/key/headlamp rotation_period=24h
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/provider/headlamp \
  allowed_client_ids="*" \
  issuer="https://vault.sudhanva.me"

Vault appends the provider path automatically, so the resulting issuer becomes `https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp`.
```

Create the client. Then record its ID and its secret.

```bash
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/client/headlamp \
  redirect_uris="https://headlamp.sudhanva.me/oidc-callback"
kubectl -n vault exec -it vault-0 -- vault read -field=client_id identity/oidc/client/headlamp
kubectl -n vault exec -it vault-0 -- vault read -field=client_secret identity/oidc/client/headlamp
```

### Step 2: Enable a Vault login method for users

Users must authenticate to Vault before Vault can issue OIDC codes. Enable a login method (for example `userpass`). Then give it access to the authorize endpoint.

```bash
kubectl -n vault exec -it vault-0 -- vault auth enable userpass
kubectl -n vault exec -it vault-0 -- /bin/sh -c 'cat > /tmp/headlamp-oidc.hcl <<EOF
path "identity/oidc/provider/headlamp/authorize" {
  capabilities = ["read"]
}
EOF'
kubectl -n vault exec -it vault-0 -- vault policy write headlamp-oidc /tmp/headlamp-oidc.hcl
kubectl -n vault exec -it vault-0 -- vault write auth/userpass/users/headlamp \
  password="REPLACE_ME" policies="default,headlamp-oidc"
```

To authorize the user for the Headlamp OIDC client, create an entity, an alias, and an assignment. Then attach the assignment to the client.

```bash
kubectl -n vault exec -it vault-0 -- vault auth list
kubectl -n vault exec -it vault-0 -- vault write -format=json identity/entity name="headlamp"
kubectl -n vault exec -it vault-0 -- vault write identity/entity-alias name="headlamp" \
  canonical_id="REPLACE_WITH_ENTITY_ID" mount_accessor="REPLACE_WITH_USERPASS_ACCESSOR"
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/assignment/headlamp \
  entity_ids="REPLACE_WITH_ENTITY_ID"
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/client/headlamp \
  client_id="REPLACE_WITH_CLIENT_ID" \
  client_secret="REPLACE_WITH_CLIENT_SECRET" \
  redirect_uris="https://headlamp.sudhanva.me/oidc-callback" \
  assignments="headlamp"
```

When Vault asks for credentials during the OIDC flow, log in with the userpass credentials.

If you want to let all authenticated Vault users log in (no assignments), make the client again without assignments. Vault then makes a new client ID and secret. After this change, update the KV entry and the Kubernetes API server flags.

### Step 3: Store Headlamp OIDC settings in Vault

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/headlamp/oidc \
  client_id="REPLACE_ME" \
  client_secret="REPLACE_ME" \
  issuer_url="https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp" \
  callback_url="https://headlamp.sudhanva.me/oidc-callback" \
  scopes="openid"
```

### Step 4: Configure Kubernetes API server OIDC

Add the OIDC settings to the API server configuration. Use the `client_id` that Vault returns.

In K3s, configure `--kube-apiserver-arg` in `/etc/rancher/k3s/config.yaml` or in the Ansible variables (`ansible/group_vars/all.yaml`). Then restart the `k3s` service on the control plane.

### Step 4a: Make sure that cluster DNS resolves Vault

The API server and the Headlamp pods must connect to `vault.sudhanva.me` to validate and exchange OIDC tokens. Tailscale DNS returns Tailscale IPs (`100.x.x.x`), and pods cannot route directly to these IPs.

This repo uses split-horizon DNS to solve this problem. CoreDNS rewrites `*.sudhanva.me` queries to the internal gateway service. Pods can reach this service through the cluster network.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: coredns
  namespace: kube-system
data:
  Corefile: |
    sudhanva.me:53 {
        errors
        cache 30
        rewrite name regex (.*)\.sudhanva\.me gateway-internal.envoy-gateway.svc.cluster.local answer auto
        kubernetes cluster.local in-addr.arpa ip6.arpa {
            pods insecure
            fallthrough in-addr.arpa ip6.arpa
            ttl 30
        }
    }
```

The `gateway-internal` service in the `envoy-gateway` namespace selects Envoy pods by label. Thus it follows the gateway without hardcoded IPs.

```yaml
apiVersion: v1
kind: Service
metadata:
  name: gateway-internal
  namespace: envoy-gateway
spec:
  type: ClusterIP
  selector:
    gateway.envoyproxy.io/owning-gateway-name: tailscale-gateway
    gateway.envoyproxy.io/owning-gateway-namespace: tailscale
  ports:
  - name: https
    port: 443
    targetPort: 10443
```

These manifests are in `infrastructure/coredns/configmap.yaml` and `infrastructure/gateway/internal-service.yaml`.

### Step 5: Sync Headlamp and log in

Headlamp reads the OIDC configuration from the `headlamp-oidc` Secret. External Secrets creates this Secret. After ArgoCD syncs the app, click the Sign In button.

## Troubleshooting OIDC

### "invalid child issuer \"provider\""

This error tells you that the issuer URL in Vault does not include the provider name. Examine the URL that Headlamp uses.

```bash
kubectl -n headlamp get secret headlamp-oidc -o jsonpath='{.data.issuer_url}' | base64 -d; echo
```

The URL must end with `/v1/identity/oidc/provider/headlamp`.

If the provider does not exist, the OIDC discovery endpoint returns `404`.

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp/.well-known/openid-configuration
```

Create the provider and the client in Vault (Step 1). Update `kv/headlamp/oidc`. Then force a refresh.

```bash
kubectl -n headlamp annotate externalsecret headlamp-oidc \
  reconcile.external-secrets.io/requested-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite
```

### OIDC not enabled on the API server

Headlamp OIDC tokens work only if the API server has the OIDC flags. Examine the flags of the running process on node `legion`.

```bash
ssh sudhanva@100.66.139.118 "ps aux | grep k3s | grep oidc"
```

If the OIDC flags are not there, add the `kube-apiserver-arg` entries to `/etc/rancher/k3s/config.yaml`. Then restart K3s.

## Optional OIDC Manifest Wiring

To move Headlamp from in-cluster service account authentication to an external OIDC provider, configure an ExternalSecret for the OIDC client credentials. Then mount the credentials in `apps/headlamp/deployment.yaml`.

## OIDC Admin Access

If Headlamp users authenticate as external OIDC identities, bind their OIDC group or user entity to `cluster-admin`.

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: headlamp-oidc-admin
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-admin
subjects:
- apiGroup: rbac.authorization.k8s.io
  kind: Group
  name: oidc:admins
```

If your OIDC provider uses a different group claim, change the group name. To bind one specific Vault OIDC user, set the `User` subject to `oidc:<entity_id>` from Vault.

```bash
kubectl -n vault exec -it vault-0 -- vault read -field=id identity/entity/name/headlamp
```

## Prometheus Metrics

Headlamp exposes `/metrics` when `HEADLAMP_CONFIG_METRICS_ENABLED` is set. The repo sets this flag. It also adds a ServiceMonitor, so Prometheus finds the endpoint automatically.

```bash
kubectl -n headlamp get servicemonitors
```
