---
title: Kubescape Security Scanning for Kubernetes
description: Enable Kubescape security scanning in offline mode for Kubernetes configuration and vulnerability analysis. View workload security scans and image vulnerability reports.
keywords:
  - kubescape kubernetes
  - kubernetes security scanning
  - vulnerability scanning
  - workload configuration scan
  - kubernetes security posture
  - kubescape operator
  - container vulnerability scan
sidebar:
  order: 12
---

# Kubescape Security Scanning

This guide enables Kubescape in offline mode for lightweight configuration and vulnerability scanning.

## Step 1: Sync the Kubescape application

ArgoCD deploys Kubescape from `infrastructure/kubescape/`.

```bash
kubectl -n argocd get applications | rg kubescape
```

## Step 2: Verify the pods

```bash
kubectl -n kubescape get pods
```

## Step 3: View scan results

Configuration scans:

```bash
kubectl get workloadconfigurationscans -A
```

Image vulnerability scans:

```bash
kubectl get vulnerabilitymanifests -A
```

## Step 4: Tune what gets scanned

Edit `infrastructure/kubescape/kubescape.yaml` to adjust capabilities or namespace filters, then let ArgoCD sync.

The defaults keep admission control and runtime detections disabled to avoid disrupting workloads.
