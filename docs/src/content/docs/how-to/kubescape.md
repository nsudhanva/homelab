---
title: Kubescape Security Scanning for Kubernetes
description: Enable Kubescape in offline mode to scan Kubernetes configuration and vulnerabilities. See workload security scans and image vulnerability reports.
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

This guide shows how to enable Kubescape in offline mode. In this mode, Kubescape does lightweight configuration and vulnerability scans.

## Step 1: Sync the Kubescape application

ArgoCD deploys Kubescape from `infrastructure/kubescape/`. Run this command to find the application:

```bash
kubectl -n argocd get applications | rg kubescape
```

## Step 2: Verify the pods

Run this command to examine the pods:

```bash
kubectl -n kubescape get pods
```

## Step 3: View scan results

To see the configuration scans, run this command:

```bash
kubectl get workloadconfigurationscans -A
```

To see the image vulnerability scans, run this command:

```bash
kubectl get vulnerabilitymanifests -A
```

## Step 4: Tune what gets scanned

To change the capabilities or namespace filters, edit `infrastructure/kubescape/kubescape.yaml`. Then let ArgoCD sync the change.

By default, admission control and runtime detections are disabled. This prevents interruptions to workloads.
