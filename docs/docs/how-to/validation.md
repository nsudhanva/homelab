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
kubectl get httproute -A
```

If a route is not accepting, describe it to see conditions:

```bash
kubectl describe httproute <name> -n <namespace>
```

Hubble UI is available at `https://hubble.sudhanva.me` from a Tailnet client once the HTTPRoute syncs.

## Step 4: Run local checks before push

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
```
