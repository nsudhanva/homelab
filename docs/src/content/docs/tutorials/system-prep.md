---
title: Bare-Metal Host Preparation
description: Prepare the bare-metal Ubuntu 26.04 LTS host machine. Configure networking, dedicated SSD storage at /home/k3s-storage, and NVIDIA GPU drivers.
keywords:
  - ubuntu 26.04 bare metal
  - host preparation kubernetes
  - k3s storage partition
  - nvidia driver ubuntu
  - bare metal server setup
sidebar:
  order: 3
---

# Host Preparation

This tutorial guides you through preparing a physical machine (node `legion`) running Ubuntu 26.04 LTS to serve as a Kubernetes node.

## Step 1: Install Ubuntu 26.04 LTS

Install Ubuntu 26.04 LTS Server on the machine. During installation:

- Select standard OpenSSH server installation.
- Configure a static IPv4 address on your local network (for example, `10.0.0.133`).
- Set the hostname to `legion`.

## Step 2: Prepare the local storage mount

The homelab uses K3s built-in Local-Path Provisioner. Workloads persist their data to `/home/k3s-storage`, which should reside on a dedicated high-speed SSD or NVMe partition.

Format the partition with `ext4` or `xfs` and mount it to `/home/k3s-storage`:

```bash
sudo mkdir -p /home/k3s-storage
sudo chmod 0777 /home/k3s-storage
```

Add the mount to `/etc/fstab` to persist it across reboots:

```text
UUID=<storage-partition-uuid> /home/k3s-storage ext4 defaults,noatime 0 2
```

## Step 3: Install NVIDIA GPU drivers (Optional for GPU Nodes)

If your bare-metal node includes an NVIDIA GPU (such as the GeForce GTX 1050 Ti on `legion`), install the proprietary NVIDIA driver:

```bash
sudo apt update
sudo apt install -y nvidia-driver-580
```

Reboot the node to initialize the NVIDIA kernel module:

```bash
sudo reboot
```

After rebooting, verify driver initialization:

```bash
nvidia-smi
```

The output confirms the GPU model, driver version, and CUDA version.

## Step 4: Next steps

With the bare-metal host installed, networked, and storage mounted, proceed to [Ansible Configuration](./containerd.md) to define cluster inventory variables.
