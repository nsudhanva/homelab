---
title: Kubernetes Pod Scheduling and Node Affinity
description: Control Kubernetes pod placement with node labels, node affinity, taints, and tolerations. Configure rolling updates with no downtime.
keywords:
  - kubernetes node affinity
  - kubernetes taints tolerations
  - pod scheduling kubernetes
  - node selector kubernetes
  - rolling update kubernetes
  - kubernetes workload placement
  - kubernetes scheduling best practices
sidebar:
  order: 18
---

Use node affinity, taints, and tolerations to control the nodes on which your pods run. The cluster has one node, `legion`. These rules have an effect only when the cluster has more than one node. Refer to [Add a Worker Node](/how-to/add-worker-node/).

## Concepts

### Node Labels

A node has labels, which are key-value pairs. Standard labels include:

- `kubernetes.io/arch`: `amd64`, `arm64`
- `kubernetes.io/os`: `linux`
- `node-role.kubernetes.io/control-plane`: `true` (K3s sets it on server nodes)

The `k3s_server` Ansible role adds these labels to `legion` through `ansible/roles/k3s_server/templates/config.yaml.j2`:

- `node.homelab/role=controlplane`
- `gpu.nvidia.com/present=true`

The GPU Operator also adds `nvidia.com/gpu.*` labels, such as `nvidia.com/gpu.product`.

No node has the label `node-role.kubernetes.io/worker`.

Add node labels through Ansible. Do not use `kubectl label`. A label that you add by hand is lost when you rebuild the node.

### Node Affinity

Affinity limits the nodes on which the scheduler can put your pod.

- `requiredDuringSchedulingIgnoredDuringExecution`: The pod must run on a matching node. If no node matches, the pod stays `Pending`.
- `preferredDuringSchedulingIgnoredDuringExecution`: The scheduler tries to find a matching node. If it finds no matching node, it puts the pod on a different node.

### Rolling Updates with No Downtime

Configure the `RollingUpdate` strategy with these values to keep a Deployment available during an update:

- `maxUnavailable: 0`: Kubernetes does not stop the old pods until the new pods are `Ready`.
- `maxSurge: 1`: Kubernetes can create one pod more than the desired count during an update.

## Example: Prefer a Specific Worker Node

This example tells the scheduler to prefer a node with the label `node-role.kubernetes.io/worker=worker`. No manifest in this repository uses this rule, and no node has this label. On a cluster with a worker node that has this label, the pod goes to the worker first. If the worker is not available, the pod goes to the control plane.

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
spec:
  replicas: 1
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    spec:
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
          - weight: 100
            preference:
              matchExpressions:
              - key: node-role.kubernetes.io/worker
                operator: In
                values:
                - worker
      containers:
      - name: my-app
        image: my-image:latest
```

## Taints and Tolerations

A taint keeps pods off a node. A pod must have a matching toleration to run on a tainted node.

Example taint:

```bash
kubectl taint nodes <node-name> key=value:NoSchedule
```

Example toleration:

```yaml
tolerations:
- key: "key"
  operator: "Equal"
  value: "value"
  effect: "NoSchedule"
```

## Limit Affinity Rules

Do not pin every application to a specific node. When all workloads have `affinity` or `nodeSelector` rules, Kubernetes cannot move pods to a different node when a node fails.

### When to use Affinity

- Hardware requirements: The app needs a specific GPU, USB device, or CPU architecture (ARM64 or AMD64) that only some nodes have.
- Performance and cost: The app is not critical and can run on a slower or less expensive node.
- Data location: Kubernetes handles this case without affinity. When a pod uses a local-path PVC, Kubernetes puts the pod on the node that has the volume.

### Shared Volumes and Affinity

Do not force a pod onto a node when the pod shares a volume with other pods. This example uses the hypothetical nodes `node-1` and `node-2`.

- Scenario: Filebrowser shares the `jellyfin-media` volume with Jellyfin.
- Constraint 1: Jellyfin must run on `node-1`, because `node-1` has the GPU.
- Constraint 2: A local-path volume stays on the node where the provisioner created it, so the shared volume is on `node-1`.
- Error: An affinity rule that forces Filebrowser to `node-2` causes a deadlock, because the volume cannot move with the pod.
- Fix: Remove the affinity rule. Kubernetes then puts the two pods on the same node.
