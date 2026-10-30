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

This tutorial shows how to prepare a physical machine (node `legion`) with Ubuntu 26.04 LTS for use as a Kubernetes node.

## Step 1: Install Ubuntu 26.04 LTS

Install Ubuntu 26.04 LTS Server on the machine. During the installation, do these steps:

- Select the standard OpenSSH server installation.
- Connect the machine to your local network. You can use DHCP, because the cluster uses the Tailscale IP of the node, not its LAN address.
- Set the hostname to `legion`.

## Step 2: Prepare the local storage mount

The homelab uses the K3s built-in Local-Path Provisioner. Workloads keep their data in `/home/k3s-storage`. Put this directory on a dedicated fast SSD or NVMe partition.

Format the partition with `ext4` or `xfs`. Then mount it at `/home/k3s-storage`:

```bash
sudo mkdir -p /home/k3s-storage
sudo chmod 0777 /home/k3s-storage
```

To keep the mount after a reboot, add it to `/etc/fstab`:

```text
UUID=<storage-partition-uuid> /home/k3s-storage ext4 defaults,noatime 0 2
```

## Step 3: Install NVIDIA GPU drivers (Optional for GPU Nodes)

If your bare-metal node has an NVIDIA GPU (such as the GeForce GTX 1050 Ti on `legion`), install the proprietary NVIDIA driver:

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

K3s uses the Tailscale IP as the node IP. If Tailscale is not installed, provisioning fails at an early stage.

Install Tailscale and join the node to your tailnet:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

In the inventory, use the address from `tailscale ip -4` for `ansible_host`, `k3s_node_ip`, and `k3s_external_ip`.

## Step 5: Next steps

The bare-metal host now has the operating system, the network, and the storage mount. Go to [Ansible Configuration](/tutorials/containerd/) to define the cluster inventory variables.
