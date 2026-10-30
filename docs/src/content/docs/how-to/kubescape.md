---
title: Kubescape Security Scanning for Kubernetes
description: Run Kubescape in offline mode to scan the Kubernetes configuration and the container images, and read the scan results.
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

This guide shows how to operate Kubescape in offline mode. In this mode, Kubescape does configuration scans and vulnerability scans in the cluster.

## Step 1: Sync the Kubescape application

ArgoCD deploys the `kubescape-operator` chart from `infrastructure/kubescape/`. Run this command to find the application:

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

## Step 4: Change the scan scope

To change the capabilities or the namespace filters, edit `infrastructure/kubescape/kubescape.yaml`. Then let ArgoCD sync the change.

The values set `admissionController`, `runtimeDetection`, and `runtimeObservability` to `disable`. Kubescape does not block or stop workloads.
