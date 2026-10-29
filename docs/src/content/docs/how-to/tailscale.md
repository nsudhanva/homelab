---
title: Tailscale Ingress and Split-Horizon DNS
description: Configure the Tailscale Gateway API for Kubernetes ingress. Configure split-horizon DNS, ExternalDNS, and cert-manager wildcard certificates for custom domains.
keywords:
  - tailscale kubernetes
  - tailscale gateway api
  - split horizon dns
  - kubernetes ingress tailscale
  - tailscale operator
  - externaldns cloudflare
  - cert-manager dns01
  - tailscale oauth
sidebar:
  order: 9
---

# Tailscale

## Step 1: Set up Tailscale

### Install Tailscale Client

```bash
curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/noble.noarmor.gpg | sudo gpg --dearmor -o /usr/share/keyrings/tailscale-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/tailscale-archive-keyring.gpg] https://pkgs.tailscale.com/stable/ubuntu noble main" | sudo tee /etc/apt/sources.list.d/tailscale.list
sudo apt-get update
sudo apt-get install -y tailscale
sudo tailscale up
```

### Update ACL tag owners

Make sure that the Tailscale ACL lets the operator tag devices. Set a real owner for `tag:k8s-operator`. Then let `tag:k8s-operator` own `tag:k8s`:

```json
{
  "tagOwners": {
    "tag:k8s-operator": ["autogroup:admin"],
    "tag:k8s": ["tag:k8s-operator"]
  }
}
```

### Create OAuth Secret

If Vault and External Secrets are configured, put the OAuth credentials in Vault. External Secrets Operator then creates the `operator-oauth` secret.

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/operator-oauth client_id=YOUR_CLIENT_ID client_secret=YOUR_CLIENT_SECRET
```

External Secrets Operator syncs the secret with `infrastructure/external-secrets/external-secret-tailscale-operator.yaml`. If you did not initialize Vault, follow the Vault setup guide.

If Vault is not set up, create the secret manually for bootstrap.

Get the OAuth credentials from https://login.tailscale.com/admin/settings/oauth. Create them with the `devices:write` scope and the tag `tag:k8s`.

```bash
kubectl create namespace tailscale
kubectl create secret generic operator-oauth \
  --namespace tailscale \
  --from-literal=client_id=YOUR_CLIENT_ID \
  --from-literal=client_secret=YOUR_CLIENT_SECRET
```

:::warning

Create the `operator-oauth` secret before you apply `bootstrap/root.yaml`. If you do not, the Tailscale Operator does not deploy correctly.

:::

### Enable SSH for Remote Access

```bash
sudo apt-get install -y openssh-server
sudo systemctl enable --now ssh
```

### Remote kubectl Access

From a different tailnet device, connect with SSH and run kubectl:

```bash
ssh user@<tailscale-hostname> kubectl get pods -A
```

As an alternative, copy the kubeconfig to your other machine:

```bash
mkdir -p ~/.kube
scp user@<tailscale-hostname>:~/.kube/config ~/.kube/config
sed -i 's|server: https://.*:6443|server: https://<tailscale-hostname>:6443|' ~/.kube/config
kubectl get pods -A
```

If the kubeconfig is not on the node, create it first:

```bash
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $(id -u):$(id -g) ~/.kube/config
```

### Node DNS

Cluster nodes do not use Tailscale DNS. The `tailscale` Ansible role runs `tailscale set --accept-dns=false` on each node. Thus, the host resolves names through its uplink resolvers. Image pulls and other node DNS lookups do not depend on DNS services in the cluster. Refer to [Node Networking and DNS](../explanation/node-networking.md).

### Configure tailnet nameservers

In the Tailscale admin console, go to **DNS** and set these values:

- Global nameserver: the Tailscale IP of `technitium-dns` (`kubectl -n technitium get svc technitium-tailscale -o wide`)
- Secondary global nameserver: a public resolver such as `1.1.1.1`. Tailnet clients then continue to resolve names when Technitium is not available.
- Split DNS: `sudhanva.me` to the `tailscale-dns` Tailscale IP (refer to [Split DNS resolver IP](#split-dns-resolver-ip))

## Step 2: Enable custom domains with Gateway API

This repo uses Envoy Gateway, ExternalDNS, and cert-manager with the Tailscale Gateway API. Subdomains such as `homelab.sudhanva.me` resolve to the Tailscale Gateway. A different system manages the apex `sudhanva.me`.

:::note

ExternalDNS creates only the subdomain records that you annotate. These records point to the Tailscale hostname. Thus, only tailnet clients can reach them.

:::

### Create Cloudflare API token secrets

If Vault is configured, write the Cloudflare token to Vault. External Secrets Operator then creates the Kubernetes secrets:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/external-dns/cloudflare api-token=YOUR_CLOUDFLARE_API_TOKEN
kubectl -n vault exec -it vault-0 -- vault kv put kv/cert-manager/cloudflare api-token=YOUR_CLOUDFLARE_API_TOKEN
```

External Secrets Operator syncs these secrets with the manifests in `infrastructure/external-secrets/`. If Vault is not ready, create the secrets manually.

In Cloudflare, create a token with DNS edit permissions for the `sudhanva.me` zone. Put the token in the two namespaces:

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

:::note

If your cluster uses split-horizon DNS for `*.sudhanva.me`, configure cert-manager to use public recursive resolvers. This repo sets these flags in `infrastructure/cert-manager/cert-manager.yaml`:

```bash
--dns01-recursive-nameservers=1.1.1.1:53,1.0.0.1:53
--dns01-recursive-nameservers-only=true
```

:::

### Update the ACME email

Before you sync, set your email in `infrastructure/cert-manager-issuer/cluster-issuer.yaml`.

### Set the Tailscale Gateway target

In `infrastructure/gateway/gateway.yaml`, change the `external-dns.alpha.kubernetes.io/target` value. Set it to the Tailscale hostname of the Envoy Gateway service (for example, `gateway-envoy.TAILNET.ts.net`). The repo default is `GATEWAY_ENVOY_HOSTNAME`.

### Split DNS resolver IP

The split DNS resolver for `sudhanva.me` must point to the `tailscale-dns` service IP. Do not point it to the Gateway IP. The `tailscale-dns` resolver answers `*.sudhanva.me` queries with the Gateway IP. If split DNS points directly to the Gateway IP, queries time out.

The resolver runs in the `tailscale-dns` namespace. It does not run in the `tailscale` namespace.

To get the resolver IP, run:

```bash
kubectl -n tailscale-dns get svc tailscale-dns -o wide
```

To examine the answer from the resolver, get the Gateway IP:

```bash
kubectl get gateway -n tailscale tailscale-gateway -o jsonpath='{.status.addresses[*].value}' && echo
```

Compare the `IPAddress` value with the output of `dig +short <name> @100.100.100.100`.

### Public hosts outside the homelab

The `tailscale-dns` resolver answers every `*.sudhanva.me` name with the Gateway IP. A host that runs outside the homelab, such as `google.sudhanva.me` on a cloud VM, needs its own zone that forwards to public DNS. CoreDNS uses the most specific zone, so this block wins over `sudhanva.me`:

```
google.sudhanva.me:53 {
    errors
    forward . 1.1.1.1 1.0.0.1
    cache 30
}
```

Add the block to both `infrastructure/tailscale-dns/configmap.yaml` and the Corefile in `infrastructure/tailscale-dns/cronjob-updater.yaml`. The CronJob rewrites the ConfigMap every 10 minutes, so a block in only one file is lost.

## Split-horizon DNS for homelab.sudhanva.me

The docs hostname has two backends:

- Tailnet clients go to the cluster through the Tailscale Gateway.
- Public clients go to Cloudflare.

Keep the public Cloudflare record on the designated host. Add a Tailscale DNS override for the same hostname.

### Deploy the split-DNS resolver

This repo has a CoreDNS deployment that answers all `*.sudhanva.me` hostnames with the Tailscale Gateway IP. A CronJob keeps this IP the same as the Gateway status.

Sync the `infrastructure/tailscale-dns/` component. Then get the Tailscale IP of the resolver:

```bash
kubectl -n tailscale-dns get svc tailscale-dns -o wide
```

To examine the updater, look at the `tailscale-dns-updater` CronJob and the logs of its latest Job.

### Configure Cloudflare (public)

In the `sudhanva.me` zone, set `homelab.sudhanva.me` to the public hostname.

### Configure Tailscale DNS (tailnet)

In the Tailscale admin console, add a nameserver and restrict it to `sudhanva.me`:

- Nameserver: the Tailscale IP from `tailscale-dns` (not the Gateway IP)
- Restrict to domain: `sudhanva.me`

### macOS resolver fallback

If `dig` works but browsers or CLI tools cannot resolve `*.sudhanva.me`, add a resolver file. This file makes macOS send `sudhanva.me` queries to Tailscale:

```bash
sudo mkdir -p /etc/resolver
echo "nameserver 100.100.100.100" | sudo tee /etc/resolver/sudhanva.me
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

### Keep ExternalDNS from overriding public DNS

The docs HTTPRoute does not have the ExternalDNS expose annotation. Thus, ExternalDNS does not overwrite the public record.

### Verify split-horizon behavior

On a tailnet device, run:

```bash
dig +short homelab.sudhanva.me @100.100.100.100
curl -I https://homelab.sudhanva.me
```

Expected results:

- DNS resolves to the Tailscale Gateway IP (for example, `TAILSCALE_GATEWAY_IP`).
- The response headers do not include Cloudflare headers such as `cf-ray`.

On a device that is not on the tailnet, run:

```bash
dig +short homelab.sudhanva.me @1.1.1.1
curl -I https://homelab.sudhanva.me
```

Expected results:

- DNS resolves to Cloudflare IPs.
- The response headers include `server: cloudflare`.

### Troubleshooting

If tailnet queries continue to go to Cloudflare, do these steps:

- Turn Tailscale off and then on again to refresh the DNS settings.
- Flush the macOS DNS cache:

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## Troubleshooting

### Connections to subdomains time out

If `tailscale ping <gateway-ip>` works but `curl https://subdomain.sudhanva.me` times out, examine the Tailscale ingress proxy pod. Make sure that it is running and healthy:

```bash
kubectl get pods -n tailscale -l tailscale.com/parent-resource-type=svc
```

If the proxy pod needs a refresh, restart it:

```bash
kubectl delete pod -n tailscale -l tailscale.com/parent-resource-type=svc
```

Make sure that the Envoy Gateway data plane pod is running and accepts traffic on port 10443:

```bash
kubectl get pods -n envoy-gateway
```

### Envoy returns "filter_chain_not_found"

This error in the Envoy logs means that the TLS connection has no Server Name Indication (SNI). Make sure that:

- Clients connect with the hostname (for example, `homelab.sudhanva.me`), not an IP address
- The hostname matches a configured HTTPRoute
- The certificate covers the requested hostname (examine it with `kubectl get certificate -n tailscale`)

### DNS not resolving

If subdomains do not resolve, examine these items:

- ExternalDNS logs: `kubectl logs -n external-dns -l app.kubernetes.io/instance=external-dns`
- The Cloudflare API token has DNS edit permissions
- The HTTPRoute has the `external-dns.alpha.kubernetes.io/expose: "true"` annotation

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
