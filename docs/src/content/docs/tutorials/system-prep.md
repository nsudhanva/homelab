---
title: System Preparation
description: Manual system preparation steps for Kubernetes nodes on Ubuntu, including swap, kernel modules, and sysctl.
keywords:
  - kubernetes system prep
  - disable swap
  - sysctl kubernetes
  - ubuntu 24.04 k8s
---

# System Preparation

:::note

The `provision-*.yaml` playbooks run the `base` role, which disables swap, loads kernel modules, writes sysctl and inotify settings, and installs base packages. Use this only if you are doing a manual setup.

:::

### Disable Swap (Permanently)

:::warning

Kubernetes requires swap to be disabled. If swap re-enables after reboot, kubelet will fail to start.

:::

```bash
sudo swapoff -a
sudo sed -i '/\sswap\s/ s/^/#/' /etc/fstab
cat /etc/fstab | grep swap
free -h
```

### Load Kernel Modules

```bash
cat <<EOF | sudo tee /etc/modules-load.d/k8s.conf
overlay
br_netfilter
EOF

sudo modprobe overlay
sudo modprobe br_netfilter
```

### Configure Sysctl

```bash
cat <<EOF | sudo tee /etc/sysctl.d/k8s.conf
net.bridge.bridge-nf-call-iptables  = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward                 = 1
EOF

sudo sysctl --system
```

### Increase Inotify Limits

:::note

Many containers (Jellyfin, Longhorn, etc.) require higher inotify limits. Without this, containers crash with "too many open files" errors.

:::

```bash
sudo sysctl -w fs.inotify.max_user_instances=512
sudo sysctl -w fs.inotify.max_user_watches=524288
echo "fs.inotify.max_user_instances=512" | sudo tee /etc/sysctl.d/99-inotify.conf
echo "fs.inotify.max_user_watches=524288" | sudo tee -a /etc/sysctl.d/99-inotify.conf
```
