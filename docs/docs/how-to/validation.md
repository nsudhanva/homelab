---
sidebar_position: 11
---

# Validation

## Phase 11: Validate the Cluster

```bash
kubectl get nodes
kubectl get pods -A
```

## Testing

Before pushing changes:

```bash
pre-commit run --all-files
kubectl get nodes
kubectl get pods -A
```
