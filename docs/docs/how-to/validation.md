---
sidebar_position: 2
title: Validation
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

If a route is not accepting, describe it to see conditions:

```bash
kubectl describe httproute <name> -n <namespace>
```

Hubble UI is available at `https://hubble.sudhanva.me` from a Tailnet client once the HTTPRoute syncs.

### Validate split-horizon DNS

On a tailnet client, `docs.sudhanva.me` should resolve to the Tailscale Gateway IP:

```bash
dig +short docs.sudhanva.me @100.100.100.100
curl -I https://docs.sudhanva.me
```

Off the tailnet, it should resolve to Cloudflare:

```bash
dig +short docs.sudhanva.me @1.1.1.1
curl -I https://docs.sudhanva.me
```

## Step 4: Validate External Secrets

If `infra-external-secrets` is Degraded, verify the Vault token secret and ClusterSecretStore:

```bash
kubectl -n external-secrets get secret vault-eso-token
kubectl -n external-secrets get clustersecretstore vault -o yaml
kubectl -n external-dns get externalsecret cloudflare-api-token -o yaml
```

## Step 5: Run local checks before push

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
```
