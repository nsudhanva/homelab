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

Update the `external-dns.alpha.kubernetes.io/target` value in `infrastructure/gateway/gateway.yaml` to the Tailscale hostname created by the Envoy Gateway service (for example, `gateway-envoy.<tailnet>.ts.net`). The repo default uses `gateway-envoy.ainu-herring.ts.net`.
