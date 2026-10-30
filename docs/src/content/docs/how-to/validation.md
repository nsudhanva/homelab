---
title: Validate Kubernetes Cluster Health
description: Examine cluster health, GitOps sync status, Tailscale ingress, External Secrets, and split-horizon DNS. Run the validation checks before you push.
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

This guide gives the checks for the cluster, GitOps sync, tailnet ingress, and External Secrets.

## Step 1: Validate the cluster

```bash
kubectl get nodes
kubectl get pods -A
```

## Step 2: Validate GitOps sync

```bash
kubectl get apps -n argocd
```

## Step 3: Validate tailnet ingress

```bash
kubectl get gatewayclass
kubectl get gateways -n tailscale
kubectl get certificates -n tailscale
kubectl get pods -n tailscale
kubectl get pods -n envoy-gateway
kubectl get svc -n tailscale-dns
kubectl get httproute -A
```

If a route does not show the `Accepted` condition, describe the route to see its conditions:

```bash
kubectl describe httproute <name> -n <namespace>
```

When the HTTPRoute is synced, a tailnet client can open the Homer dashboard at `https://home.sudhanva.me`.

### Validate split-horizon DNS

On a tailnet client, `homelab.sudhanva.me` must resolve to the Tailscale Gateway IP:

```bash
dig +short homelab.sudhanva.me @100.100.100.100
curl -I https://homelab.sudhanva.me
```

Validate one more app hostname on the Gateway:

```bash
dig +short home.sudhanva.me @100.100.100.100
curl -I https://home.sudhanva.me
```

On a device that is not on the tailnet, the manual public record returns the same Tailscale Gateway IP. The `curl` command fails, because the device has no route to the tailnet.

```bash
dig +short homelab.sudhanva.me @1.1.1.1
curl -I https://homelab.sudhanva.me
```

## Step 4: Validate External Secrets

If `infra-external-secrets` is `Degraded`, examine the ClusterSecretStore and an ExternalSecret:

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
