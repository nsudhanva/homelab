---
sidebar_position: 3
title: Install Containerd
---

# Install Containerd

:::note

This step is handled by the Ansible provisioning playbooks. Use this only if you are doing a manual setup.

:::

```bash
sudo apt-get update
sudo apt-get install -y containerd
sudo mkdir -p /etc/containerd
containerd config default | sudo tee /etc/containerd/config.toml > /dev/null
sudo sed -i 's/SystemdCgroup = false/SystemdCgroup = true/g' /etc/containerd/config.toml
sudo systemctl restart containerd
sudo systemctl enable containerd
```
