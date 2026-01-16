---
title: Expose Headlamp With Tailscale Gateway
---

# Expose Headlamp With Tailscale Gateway

This guide shows how to deploy the Headlamp UI and expose it at `headlamp.sudhanva.me` through the Tailscale Gateway API.

## Step 1: Add the Headlamp app manifests

Create a new app directory under `apps/` with separate manifests for each resource.

Example layout:

- `apps/headlamp/app.yaml`
- `apps/headlamp/namespace.yaml`
- `apps/headlamp/serviceaccount.yaml`
- `apps/headlamp/clusterrolebinding.yaml`
- `apps/headlamp/deployment.yaml`
- `apps/headlamp/service.yaml`
- `apps/headlamp/httproute.yaml`

`app.yaml` defines the app name, path, and namespace.

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

ArgoCD watches the repo and applies changes via ApplicationSets.

```bash
git add apps/headlamp
git commit -m "Add headlamp app"
git push
```

## Step 3: Access Headlamp

Open `https://headlamp.sudhanva.me` in your browser. Use a service account token to authenticate.

```bash
kubectl -n headlamp create token headlamp
```

## Step 4: Adjust permissions if needed

The default setup binds the Headlamp service account to the built-in `view` role. If you want admin access, update the ClusterRoleBinding to use `cluster-admin` or another role.

## OIDC Login With Vault

This enables long-lived OIDC logins instead of short-lived service account tokens. It uses Vault as the identity provider and requires the Kubernetes API server to trust Vault as an OIDC issuer.

### Step 1: Create Vault OIDC key, provider, and client

Log into Vault with an admin token:

```bash
kubectl -n vault exec -it vault-0 -- vault login
```

Create a signing key and provider:

```bash
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/key/headlamp rotation_period=24h
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/provider/headlamp \
  allowed_client_ids="*" \
  issuer="https://vault.sudhanva.me"

Vault appends the provider path automatically, so the resulting issuer becomes `https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp`.
```

Create the client and capture its ID and secret:

```bash
kubectl -n vault exec -it vault-0 -- vault write identity/oidc/client/headlamp \
  redirect_uris="https://headlamp.sudhanva.me/oidc-callback"
kubectl -n vault exec -it vault-0 -- vault read -field=client_id identity/oidc/client/headlamp
kubectl -n vault exec -it vault-0 -- vault read -field=client_secret identity/oidc/client/headlamp
```

### Step 2: Enable a Vault login method for users

Vault must allow humans to authenticate before it can issue OIDC codes. Enable a login method (for example `userpass`) and grant it access to the authorize endpoint.

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

Authorize the user for the Headlamp OIDC client by creating an entity, alias, and assignment, then attach that assignment to the client:

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

Use the userpass credentials to log in when Vault prompts during the OIDC flow.

If you prefer to allow any authenticated Vault user (no assignments), recreate the client without assignments. Vault will generate a new client ID and secret, so update the KV entry and the Kubernetes API server flags after doing this.

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

Update your kubeadm config to include OIDC settings. Use the `client_id` returned by Vault.

```yaml
apiServer:
  extraArgs:
    oidc-issuer-url: https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp
    oidc-client-id: REPLACE_WITH_VAULT_CLIENT_ID
    oidc-username-claim: sub
    oidc-groups-claim: groups
    oidc-username-prefix: "oidc:"
    oidc-groups-prefix: "oidc:"
```

Apply the change using your kubeadm workflow and restart the API server. This is a control plane change and should be done directly on the control plane node.

If you edit the static manifest directly, keep the `oidc:` prefixes quoted to avoid YAML parsing errors.

### Step 4a: Ensure cluster DNS resolves Vault

The API server and Headlamp pods must be able to reach `vault.sudhanva.me` for OIDC token validation and exchange. Tailscale DNS returns Tailscale IPs (`100.x.x.x`) that pods cannot route to directly.

This repo uses split-horizon DNS to solve this. CoreDNS rewrites `*.sudhanva.me` queries to the internal gateway service, which pods can reach via the cluster network:

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

The `gateway-internal` service in `envoy-gateway` namespace selects Envoy pods by label, so it dynamically tracks the gateway without hardcoded IPs:

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

These manifests live in `infrastructure/coredns/configmap.yaml` and `infrastructure/gateway/internal-service.yaml`.

### Step 5: Sync Headlamp and log in

Headlamp reads OIDC config from the `headlamp-oidc` Secret created by External Secrets. After ArgoCD syncs the app, use the Sign In button.

## Troubleshooting OIDC

### "invalid child issuer \"provider\""

This error means the issuer URL stored in Vault is missing the provider name. Confirm what Headlamp is using:

```bash
kubectl -n headlamp get secret headlamp-oidc -o jsonpath='{.data.issuer_url}' | base64 -d; echo
```

The URL must end with `/v1/identity/oidc/provider/headlamp`.

If the provider does not exist, the OIDC discovery endpoint returns `404`:

```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  https://vault.sudhanva.me/v1/identity/oidc/provider/headlamp/.well-known/openid-configuration
```

Create the provider and client in Vault (Step 1 above), update `kv/headlamp/oidc`, then force a refresh:

```bash
kubectl -n headlamp annotate externalsecret headlamp-oidc \
  reconcile.external-secrets.io/requested-at="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --overwrite
```

### OIDC not enabled on the API server

Headlamp OIDC tokens only work if the API server has OIDC flags set. Check the running flags:

```bash
kubectl -n kube-system get pods -l component=kube-apiserver \
  -o jsonpath='{.items[0].spec.containers[0].command}' | tr ' ' '\n' | rg oidc
```

If no OIDC flags are present, add them via your kubeadm config and restart the API server as described in Step 4.

## Repo Wiring For OIDC

These files implement the OIDC wiring for Headlamp:

- `apps/headlamp/external-secret-oidc.yaml`
- `apps/headlamp/deployment.yaml`

## OIDC Admin Access

Headlamp users authenticate as OIDC identities. To grant full admin access, bind an OIDC group to `cluster-admin`.

Use a separate manifest so ArgoCD can manage it:

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

The repo includes `apps/headlamp/clusterrolebinding-oidc.yaml`. Update the group name if your OIDC provider uses a different group claim.

If you prefer binding a specific OIDC user, set the `User` entry to `oidc:<entity_id>` from Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault read -field=id identity/entity/name/headlamp
```

## Prometheus Metrics

Headlamp exposes `/metrics` when `HEADLAMP_CONFIG_METRICS_ENABLED` is set. The repo enables this flag and adds a ServiceMonitor so Prometheus picks it up automatically.

```bash
kubectl -n headlamp get servicemonitors
```
