---
sidebar_position: 9
---

# Storage (Longhorn)

## Phase 8: Storage Prerequisites (Longhorn)

### Install Required Packages

```bash
sudo apt-get update
sudo apt-get install -y open-iscsi nfs-common cryptsetup
sudo systemctl enable --now iscsid
```

### Create Storage Directory

> [!IMPORTANT]
> Longhorn needs a storage directory to exist. Create it on your preferred disk.

```bash
mkdir -p /home/your-username/longhorn-storage
```

> [!NOTE]
> Update the matching path in `bootstrap/templates/longhorn.yaml` and `ansible/group_vars/all.yaml`.

### Add Node Label for Longhorn Disk

> [!NOTE]
> With `createDefaultDiskLabeledNodes: true`, Longhorn only creates disks on nodes with this label.

```bash
kubectl label node $(hostname) node.longhorn.io/create-default-disk=true --overwrite
```
