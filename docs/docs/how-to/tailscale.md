---
sidebar_position: 4
title: Tailscale
---

# Tailscale

## Step 1: Set up Tailscale

### Install Tailscale Client

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### Update ACL tag owners

Ensure the Tailscale ACL allows the operator to tag devices. Set a real owner for `tag:k8s-operator`, then allow it to own `tag:k8s`:

```
{
  "tagOwners": {
    "tag:k8s-operator": ["autogroup:admin"],
    "tag:k8s": ["tag:k8s-operator"]
  }
}
```

### Create OAuth Secret

If Vault and External Secrets are configured, store the OAuth credentials in Vault and let External Secrets Operator populate the `operator-oauth` secret.

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/operator-oauth client_id=YOUR_CLIENT_ID client_secret=YOUR_CLIENT_SECRET
```

External Secrets Operator will sync the secret using `infrastructure/external-secrets/external-secret-tailscale-operator.yaml`. Follow the Vault setup guide if you have not initialized Vault yet.

If you have not set up Vault yet, create the secret manually for bootstrap:

Get OAuth credentials from https://login.tailscale.com/admin/settings/oauth (create with `devices:write` scope and tag `tag:k8s`).

```bash
kubectl create namespace tailscale
kubectl create secret generic operator-oauth \
  --namespace tailscale \
  --from-literal=client_id=YOUR_CLIENT_ID \
  --from-literal=client_secret=YOUR_CLIENT_SECRET
```

:::warning

Create the `operator-oauth` secret before applying `bootstrap/root.yaml` so the Tailscale Operator deploys cleanly.

:::

### Enable SSH for Remote Access

```bash
sudo apt-get install -y openssh-server
sudo systemctl enable --now ssh
```

### Remote kubectl Access

From another Tailnet device, SSH and run kubectl:

```bash
ssh user@<tailscale-hostname> kubectl get pods -A
```

Or copy kubeconfig to your other machine:

```bash
mkdir -p ~/.kube
scp user@<tailscale-hostname>:~/.kube/config ~/.kube/config
sed -i 's|server: https://.*:6443|server: https://<tailscale-hostname>:6443|' ~/.kube/config
kubectl get pods -A
```

## Step 2: Enable custom domains with Gateway API

This repo uses Envoy Gateway, ExternalDNS, and cert-manager with the Tailscale Gateway API setup. Subdomains such as `docs.sudhanva.me` resolve to the Tailscale Gateway while your apex `sudhanva.me` remains managed elsewhere.

:::note

ExternalDNS creates only the subdomain records you annotate. Those records point at the Tailscale hostname, so they are reachable only from tailnet clients.

:::

### Create Cloudflare API token secrets

If Vault is configured, write the Cloudflare token to Vault and let External Secrets Operator create the Kubernetes secrets:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/external-dns/cloudflare api-token=YOUR_CLOUDFLARE_API_TOKEN
kubectl -n vault exec -it vault-0 -- vault kv put kv/cert-manager/cloudflare api-token=YOUR_CLOUDFLARE_API_TOKEN
```

External Secrets Operator will sync these using the manifests in `infrastructure/external-secrets/`. If Vault is not ready yet, create the secrets manually:

Create a token in Cloudflare with DNS edit permissions for the `sudhanva.me` zone and store it in both namespaces:

```bash
kubectl create namespace external-dns
kubectl create secret generic cloudflare-api-token \
  --namespace external-dns \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN

kubectl create namespace cert-manager
kubectl create secret generic cloudflare-api-token \
  --namespace cert-manager \
  --from-literal=api-token=YOUR_CLOUDFLARE_API_TOKEN
```

### Update the ACME email

Set your email in `infrastructure/cert-manager-issuer/cluster-issuer.yaml` before syncing.

### Set the Tailscale Gateway target

Update the `external-dns.alpha.kubernetes.io/target` value in `infrastructure/gateway/gateway.yaml` to the Tailscale hostname created by the Envoy Gateway service (for example, `gateway-envoy.TAILNET.ts.net`). The repo default uses `gateway-envoy.ainu-herring.ts.net`.

## Split-horizon DNS for docs.sudhanva.me

The docs hostname serves two backends:

- Tailnet clients should hit the cluster through the Tailscale Gateway.
- Public clients should hit the Cloudflare Pages site.

Keep the public Cloudflare record pointed at Pages, and add a Tailscale DNS override for the same hostname.

### Deploy the split-DNS resolver

This repo includes a CoreDNS deployment that rewrites any `*.sudhanva.me` hostname to the Tailscale Gateway hostname and resolves it through Tailscale DNS.

Sync the `infrastructure/tailscale-dns/` component, then capture the Tailscale IP for the resolver:

```bash
kubectl -n tailscale-dns get svc tailscale-dns -o wide
```

If the Tailscale Gateway hostname changes, update it in `infrastructure/tailscale-dns/configmap.yaml`.

### Configure Cloudflare (public)

Set `docs.sudhanva.me` to the Cloudflare Pages hostname in the `sudhanva.me` zone.

### Configure Tailscale DNS (tailnet)

In the Tailscale admin console, add a nameserver and restrict it to `sudhanva.me`:

- Nameserver: the Tailscale IP from `tailscale-dns`
- Restrict to domain: `sudhanva.me`

### Keep ExternalDNS from overriding public DNS

The docs HTTPRoute intentionally omits the ExternalDNS expose annotation so ExternalDNS does not overwrite the public record.

### Verify split-horizon behavior

On a tailnet device:

```bash
dig +short docs.sudhanva.me @100.100.100.100
curl -I https://docs.sudhanva.me
```

Expected results:

- DNS resolves to the Tailscale Gateway IP (for example, `100.88.7.18`).
- Response headers do not include Cloudflare headers like `cf-ray`.

Off the tailnet:

```bash
dig +short docs.sudhanva.me @1.1.1.1
curl -I https://docs.sudhanva.me
```

Expected results:

- DNS resolves to Cloudflare IPs.
- Response headers include `server: cloudflare`.

### Troubleshooting

If tailnet queries still hit Cloudflare:

- Toggle Tailscale off/on to refresh DNS settings.
- Flush macOS DNS cache:

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## Troubleshooting

### Connections to subdomains time out

If `tailscale ping <gateway-ip>` works but `curl https://subdomain.sudhanva.me` times out, the issue is likely Cilium's socket-level LoadBalancer interfering with the Tailscale proxy's iptables DNAT rules.

**Solution:** Enable `socketLB.hostNamespaceOnly=true` in Cilium:

```bash
cilium upgrade --version $(cilium version | grep 'cilium image (running)' | awk '{print $4}') \
  --set socketLB.hostNamespaceOnly=true
kubectl rollout restart daemonset/cilium -n kube-system
```

Then restart the Tailscale proxy pod:

```bash
kubectl delete pod -n tailscale -l tailscale.com/parent-resource-type=svc
```

See [Cilium CNI](../tutorials/cilium.md) for details.

:::warning

This is a **required** configuration when using Cilium in kube-proxy replacement mode with Tailscale Kubernetes Operator LoadBalancer services.

:::

### Envoy returns "filter_chain_not_found"

This error in Envoy logs means the TLS connection is missing Server Name Indication (SNI). Ensure:

- Clients connect using the hostname (e.g., `docs.sudhanva.me`), not an IP address
- The hostname matches a configured HTTPRoute
- The certificate covers the requested hostname (check with `kubectl get certificate -n tailscale`)

### DNS not resolving

If subdomains don't resolve, check:

- ExternalDNS logs: `kubectl logs -n external-dns -l app.kubernetes.io/instance=external-dns`
- Cloudflare API token has DNS edit permissions
- The HTTPRoute has `external-dns.alpha.kubernetes.io/expose: "true"` annotation

### Verify the traffic flow

```bash
# Check Gateway is programmed
kubectl get gateways -n tailscale

# Check HTTPRoutes are accepted
kubectl describe httproute <name> -n <namespace>

# Check certificate is ready
kubectl get certificates -n tailscale

# Check Envoy logs for incoming requests
kubectl logs -n envoy-gateway -l gateway.envoyproxy.io/owning-gateway-name=tailscale-gateway -c envoy --tail=20
```
