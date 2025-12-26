---
sidebar_position: 3
title: Storage
---

# Storage (Longhorn)

## Step: Storage prerequisites for Longhorn

### Install Required Packages

```bash
sudo apt-get update
sudo apt-get install -y open-iscsi nfs-common cryptsetup
sudo systemctl enable --now iscsid
```

### Create Storage Directory

:::warning

Longhorn needs a storage directory to exist. Create it on your preferred disk.

:::

```bash
sudo mkdir -p /var/lib/longhorn
```

:::note

Update the matching path in `bootstrap/templates/longhorn.yaml` and `ansible/group_vars/all.yaml`.

:::

:::note

The default path is `/var/lib/longhorn` to avoid user-specific home directories.

:::

### Add Node Label for Longhorn Disk

:::note

With `createDefaultDiskLabeledNodes: true`, Longhorn only creates disks on nodes with this label.

:::

```bash
kubectl label node $(hostname) node.longhorn.io/create-default-disk=true --overwrite
```
