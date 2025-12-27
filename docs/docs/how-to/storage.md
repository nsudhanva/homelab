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

## Step: Resize PVCs safely

Longhorn supports volume expansion, but Kubernetes does not allow shrinking PVCs in place.

### Expanding a PVC

Update the PVC size in Git and let ArgoCD sync. Longhorn will expand the volume and filesystem.

### Reducing a PVC size (migration required)

To reduce a volume size without data loss, create a new PVC at the smaller size and copy data across.

1. Create a new PVC with the target size (for example `jellyfin-media-200`).
2. Create a temporary Pod that mounts both the old and new PVCs.
3. Copy data across and verify checksums.
4. Update the Deployment to use the new PVC.
5. Remove the old PVC once validated.

Example copy pod (replace names and namespaces):

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: pvc-migration
  namespace: jellyfin
spec:
  restartPolicy: Never
  containers:
    - name: rsync
      image: docker.io/library/alpine:3.20
      command: ["/bin/sh", "-c"]
      args:
        - apk add --no-cache rsync && rsync -aHAX --info=progress2 /old/ /new/
      volumeMounts:
        - name: old
          mountPath: /old
        - name: new
          mountPath: /new
  volumes:
    - name: old
      persistentVolumeClaim:
        claimName: jellyfin-media
    - name: new
      persistentVolumeClaim:
        claimName: jellyfin-media-200
```
