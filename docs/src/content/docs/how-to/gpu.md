---
title: GPU Support for Kubernetes Workloads
description: Enable Intel iGPU and NVIDIA GPU support for Kubernetes workloads on Talos Linux. Covers the Intel device plugin DaemonSet and the NVIDIA GPU Operator.
keywords:
  - kubernetes gpu
  - nvidia gpu kubernetes
  - nvidia gpu operator talos
  - intel gpu kubernetes
  - gpu device plugin
  - kubernetes transcoding
  - jellyfin gpu
sidebar:
  order: 16
---

# GPU Support

## Step 1: Enable Intel GPU support

Intel iGPU transcoding needs no host packages. The Intel GPU Plugin DaemonSet advertises the devices to the scheduler.

The Intel GPU plugin manifest lives in `infrastructure/gpu/intel-plugin.yaml`.

Verify after deployment:

```bash
kubectl describe node | grep gpu.intel.com/i915
```

## Step 2: Enable NVIDIA GPU support

Talos has no package manager, so the driver userspace and container runtime integration come from the NVIDIA GPU Operator. The operator deploys the driver containers, the container toolkit with CDI support, and the device plugin.

The GPU Operator Application lives in `infrastructure/gpu-operator/gpu-operator.yaml` and syncs through ArgoCD like every other component.

Verify after deployment:

```bash
kubectl describe node | grep nvidia.com/gpu
```

The legacy NVIDIA device plugin manifest lives in `infrastructure/gpu/nvidia-plugin.yaml` for clusters where the driver stack is already present on the host.

## Step 3: Request GPUs from workloads

Add a GPU resource limit to the container that needs acceleration. Jellyfin uses this pattern for transcoding.
