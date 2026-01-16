---
title: Kubernetes Cluster Setup Tutorials
description: Step-by-step tutorials for building a bare-metal Kubernetes cluster with kubeadm, Ansible, Cilium, and ArgoCD on Ubuntu 24.04.
keywords:
  - kubernetes tutorial
  - kubeadm tutorial
  - bare metal kubernetes setup
  - ansible kubernetes
  - cilium cni installation
  - argocd gitops setup
  - ubuntu 24.04 kubernetes
sidebar:
  order: 1
---

# Cluster Setup Tutorials

These tutorials walk you through building a production-ready Kubernetes cluster from scratch. Choose your path based on whether you want automated provisioning or prefer manual control.

```mermaid
flowchart TD
  Start["Start here"] --> Choice{"Provision with Ansible?"}
  Choice -->|Recommended| Ansible["Run Ansible provisioning"]
  Choice -->|Manual| Manual["Manual node preparation"]
  Ansible --> Kubeadm["kubeadm init/join"]
  Manual --> SystemPrep["System Preparation"]
  SystemPrep --> Containerd["Install Containerd"]
  Containerd --> Kubeadm
  Kubeadm --> Cilium["Install Cilium CNI"]
  Cilium --> Argo["Install ArgoCD + GitOps bootstrap"]
  Argo --> Sync["Apps and infrastructure sync"]
```

:::note

Ansible provisioning handles system prep, containerd, and Kubernetes packages. It does not run `kubeadm init/join` or install Cilium/ArgoCD.

:::

## Ansible Path (Recommended)

Use this path for reproducible, version-controlled node provisioning.

| Step | Tutorial | What You Get |
|------|----------|--------------|
| 1 | [Prerequisites](./prerequisites.md) | Workstation tools, Ansible inventory, SSH access |
| 2 | [Kubernetes](./kubernetes.md) | Control plane initialized with kubeadm |
| 3 | [Cilium CNI](./cilium.md) | eBPF networking, kube-proxy replacement |
| 4 | [ArgoCD and GitOps](./argocd.md) | GitOps continuous deployment |
| 5 | [Join Worker Nodes](./join-workers.md) | Multi-node cluster |

## Manual Path (Advanced)

Use this path when you need full control over each configuration step.

| Step | Tutorial | What You Get |
|------|----------|--------------|
| 1 | [Prerequisites](./prerequisites.md) | Workstation tools, inventory |
| 2 | [System Preparation](./system-prep.md) | Swap disabled, kernel modules, sysctl |
| 3 | [Install Containerd](./containerd.md) | Container runtime configured |
| 4 | [Kubernetes](./kubernetes.md) | Control plane initialized |
| 5 | [Cilium CNI](./cilium.md) | CNI and kube-proxy replacement |
| 6 | [ArgoCD and GitOps](./argocd.md) | GitOps deployment |
| 7 | [Join Worker Nodes](./join-workers.md) | Multi-node cluster |

## Local Development

Want to test the setup before touching hardware? Use the [Local Multipass Cluster](./local-multipass-cluster.md) tutorial to spin up VMs on your workstation.
