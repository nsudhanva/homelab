---
title: Validate Kubernetes Cluster Health
description: Examine cluster health, GitOps sync status, Tailscale ingress, External Secrets, and the split-horizon DNS configuration. Run the validation checks before you push.
keywords:
  - kubernetes cluster validation
  - kubectl get nodes
  - argocd app status
  - tailscale gateway validation
  - external secrets validation
  - split horizon dns test
  - kubernetes health check
sidebar:
  order: 14
---

# Validation

## Step 1: Validate the cluster

```bash
kubectl get nodes
kubectl get pods -A
```

## Step 2: Validate GitOps sync

```bash
kubectl get apps -n argocd
```

## Step 3: Validate Tailnet ingress

```bash
kubectl get gatewayclass
kubectl get gateways -n tailscale
kubectl get certificates -n tailscale
kubectl get pods -n tailscale
kubectl get pods -n envoy-gateway
kubectl get svc -n tailscale-dns
kubectl get httproute -A
```

If a route does not show the Accepted condition, describe the route to see its conditions:

```bash
kubectl describe httproute <name> -n <namespace>
```

After the HTTPRoute syncs, a Tailnet client can open the Homer dashboard at `https://home.sudhanva.me`.

### Validate split-horizon DNS

On a tailnet client, `homelab.sudhanva.me` must resolve to the Tailscale Gateway IP:

```bash
dig +short homelab.sudhanva.me @100.100.100.100
curl -I https://homelab.sudhanva.me
```

If the Gateway exposes other apps, validate one of them also:

```bash
dig +short home.sudhanva.me @100.100.100.100
curl -I https://home.sudhanva.me
```

Off the tailnet, the hostname must resolve to Cloudflare:

```bash
dig +short homelab.sudhanva.me @1.1.1.1
curl -I https://homelab.sudhanva.me
```

## Step 4: Validate External Secrets

If `infra-external-secrets` is Degraded, examine the ClusterSecretStore and an ExternalSecret:

```bash
kubectl -n external-secrets get clustersecretstore vault -o yaml
kubectl -n external-dns get externalsecret cloudflare-api-token -o yaml
```

## Step 5: Run local checks before push

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
```
