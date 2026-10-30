---
title: Kubernetes Pod Scheduling and Node Affinity
description: Control Kubernetes pod placement with node affinity, taints, and tolerations. Configure rolling updates for zero downtime and avoid common scheduling anti-patterns.
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

# Scheduling Workloads

Use Node Affinity, Taints, and Tolerations to control where your pods run in the cluster. The cluster has one node today (`legion`), so these rules matter only after you add more nodes. Refer to [Add a Worker Node](/how-to/add-worker-node/).

## Concepts

### Node Labels

A node can have labels, which are key-value pairs. Standard labels include:

- `kubernetes.io/arch`: `amd64`, `arm64`
- `kubernetes.io/os`: `linux`
- `node-role.kubernetes.io/control-plane`: `true` (K3s sets it on server nodes)

The `k3s_server` Ansible role adds these labels to `legion` through `ansible/roles/k3s_server/templates/config.yaml.j2`:

- `node.homelab/role=controlplane`
- `gpu.nvidia.com/present=true`

The GPU Operator also adds `nvidia.com/gpu.*` labels, such as `nvidia.com/gpu.product`.

No node has the label `node-role.kubernetes.io/worker`.

Add node labels through Ansible, not with `kubectl label`. Labels that you add by hand are lost when the node is rebuilt.

### Node Affinity

Affinity limits the nodes on which the scheduler can put your pod.

- **Required (`requiredDuringSchedulingIgnoredDuringExecution`):** The pod _must_ run on a matching node. If no node matches, the pod stays Pending.
- **Preferred (`preferredDuringSchedulingIgnoredDuringExecution`):** The scheduler tries to find a matching node. If it finds none, it schedules the pod on any node.

### Zero Downtime Strategy

To get zero downtime when you move workloads or update deployments, configure the `RollingUpdate` strategy correctly.

- **maxUnavailable: 0**: Kubernetes does not stop old pods until the new pods are Ready.
- **maxSurge: 1**: Kubernetes can create 1 pod more than the desired count during updates.

## Example: Preferring a Specific Worker Node

This example tells the scheduler to prefer a node with the label `node-role.kubernetes.io/worker=worker`. No manifest in this repo uses this rule, and no node has the label today. If you add a worker with this label, a pod with this rule goes there first and can still fall back to the control plane.

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

A taint keeps pods off a node. To run on a tainted node, a pod must have a matching `toleration`.

**Example Taint:**

```bash
kubectl taint nodes <node-name> key=value:NoSchedule
```

**Example Toleration:**

```yaml
tolerations:
- key: "key"
  operator: "Equal"
  value: "value"
  effect: "NoSchedule"
```

## Best Practices: Keep it Flexible

Do not pin every application to a specific node.

If you add `affinity` or `nodeSelector` to all workloads, you create rigid constraints. These constraints stop Kubernetes from healing itself.

### When to use Affinity

- **Hardware requirements:** The app needs a specific GPU, USB device, or architecture (ARM64 vs AMD64) that only some nodes have.
- **Performance/cost:** Move non-critical apps to a cheaper or slower node.
- **Data gravity:** Kubernetes does this for you. If a pod uses a PVC on a specific node, Kubernetes schedules the pod on that node.

### The "Filebrowser Lesson" (Anti-Pattern)

Do not force a pod onto a node if it shares dependencies with other pods.

This example uses hypothetical nodes `node-1` and `node-2`.

- **Scenario:** Filebrowser shares the `jellyfin-media` volume with Jellyfin.
- **Constraint 1:** Jellyfin _must_ run on `node-1` (GPU).
- **Constraint 2:** Local-path volumes stay on the node where they were created, so the shared volume is locked to `node-1`.
- **Error:** An affinity that forces Filebrowser to `node-2` causes a deadlock, because the volume cannot move with the pod.
- **Fix:** Remove the affinity. Let Kubernetes put the two pods on the same node.
