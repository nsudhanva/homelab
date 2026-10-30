---
title: Bare-Metal Host Preparation
description: Prepare the bare-metal Ubuntu 26.04 LTS host. Configure the network, the dedicated SSD storage at /home/k3s-storage, the NVIDIA GPU driver, and Tailscale.
keywords:
  - ubuntu 26.04 bare metal
  - host preparation kubernetes
  - k3s storage partition
  - nvidia driver ubuntu
  - bare metal server setup
sidebar:
  order: 3
---

This tutorial prepares a physical machine (node `legion`) with Ubuntu 26.04 LTS for use as a Kubernetes node.

## Step 1: Install Ubuntu 26.04 LTS

Install Ubuntu 26.04 LTS Server on the machine. During the installation, do these steps:

- Select the standard OpenSSH server installation.
- Connect the machine to your local network. DHCP is permitted, because the cluster uses the Tailscale IP of the node, not its LAN address.
- Set the hostname to `legion`.

## Step 2: Prepare the local storage mount

The cluster uses the K3s built-in Local-Path Provisioner. Workloads keep their data in `/home/k3s-storage`. Put this directory on a dedicated SSD or NVMe partition.

Format the partition with `ext4` or `xfs`. Create the mount point, and then mount the partition at `/home/k3s-storage`.

```bash
sudo mkdir -p /home/k3s-storage
sudo chmod 0700 /home/k3s-storage
```

Add the mount to `/etc/fstab`, so that the mount stays after a reboot.

```text
UUID=<storage-partition-uuid> /home/k3s-storage ext4 defaults,noatime 0 2
```

## Step 3: Install the NVIDIA GPU driver

The `nvidia` Ansible role stops the playbook if `nvidia-smi` does not run. Thus, the node must have an NVIDIA GPU and the proprietary NVIDIA driver. The node `legion` has a GeForce GTX 1050 Ti.

Install the driver:

```bash
sudo apt update
sudo apt install -y nvidia-driver-580
```

Reboot the node to load the NVIDIA kernel module:

```bash
sudo reboot
```

After the reboot, make sure that the driver is loaded:

```bash
nvidia-smi
```

The output shows the GPU model, the driver version, and the CUDA version.

## Step 4: Install and join Tailscale

K3s uses the Tailscale IP as the node IP. The `tailscale` Ansible role stops the playbook if Tailscale is not installed.

Install Tailscale and join the node to your tailnet:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

In the inventory, use the address from `tailscale ip -4` for `ansible_host`, `k3s_node_ip`, and `k3s_external_ip`.

## Step 5: Next steps

The host has the operating system, the network, the storage mount, the GPU driver, and Tailscale. Go to [Ansible Configuration](/tutorials/containerd/) to set the cluster inventory variables.
