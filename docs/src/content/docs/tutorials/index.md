---
title: K3s Cluster Setup Tutorials
description: Step-by-step tutorials to build a bare-metal K3s Kubernetes cluster on Ubuntu 26.04 LTS with Ansible automation and ArgoCD GitOps.
keywords:
  - k3s tutorial
  - bare metal kubernetes setup
  - ubuntu 26.04 kubernetes
  - ansible automation k3s
  - argocd gitops setup
sidebar:
  order: 1
---

# Cluster Setup Tutorials

These tutorials show you, step by step, how to build a bare-metal K3s Kubernetes cluster from scratch. The cluster runs on node `legion` (Ubuntu 26.04 LTS).

```mermaid
flowchart TD
  Start["Start here"] --> Prereq["Step 1: Prerequisites"]
  Prereq --> Prep["Step 2: Host Preparation"]
  Prep --> Config["Step 3: Ansible Configuration"]
  Config --> Provision["Step 4: K3s Provisioning"]
  Provision --> Argo["Step 5: ArgoCD GitOps Bootstrap"]
  Argo --> Workers["Step 6: Worker Nodes (not automated yet)"]
```

## Tutorial Roadmap

Do these tutorials in sequence. The result is a single-node cluster that you can rebuild from this repository:

| Stage | Tutorial | Deliverable |
|---|---|---|
| Step 1 | [Prerequisites](/tutorials/prerequisites/) | Workstation dependencies and access credentials |
| Step 2 | [Host Preparation](/tutorials/system-prep/) | Ubuntu 26.04 installation, networking, and storage mount |
| Step 3 | [Ansible Configuration](/tutorials/containerd/) | Inventory variables and host role definitions |
| Step 4 | [K3s Bootstrap](/tutorials/kubernetes/) | Live K3s cluster with Flannel CNI and NVIDIA CDI |
| Step 5 | [ArgoCD and GitOps](/tutorials/argocd/) | Declarative infrastructure and app synchronization |
| Step 6 | [Add Workers](/tutorials/join-workers/) | What a second node needs. The repo does not automate worker joins yet |
