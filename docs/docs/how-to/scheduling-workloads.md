---
sidebar_position: 20
---

# Scheduling Workloads

Control exactly where your pods run in the cluster using Node Affinity, Taints, and Tolerations. This guide explains how to target specific nodes (like an ARM64 worker) while ensuring high availability.

## Concepts

### Node Labels

Nodes can be labeled with key-value pairs. Standard labels include:

* `kubernetes.io/arch`: `amd64`, `arm64`
* `kubernetes.io/os`: `linux`
* `node-role.kubernetes.io/worker`: `worker`

You can add custom labels:

```bash
kubectl label node <node-name> disk=ssd
```

### Node Affinity

Affinity allows you to constrain which nodes your pod is eligible to be scheduled on.

* **Required (`requiredDuringSchedulingIgnoredDuringExecution`):** The pod *must* run on a matching node. If no match is found, the pod stays Pending.
* **Preferred (`preferredDuringSchedulingIgnoredDuringExecution`):** The scheduler tries to find a matching node. If not found, it schedules the pod anywhere.

### Zero Downtime Strategy

When moving workloads or updating deployments, ensure zero downtime by configuring the `RollingUpdate` strategy correctly.

* **maxUnavailable: 0**: Ensure no old pods are killed until new ones are Ready.
* **maxSurge: 1**: Allow creating 1 extra pod above the desired count during updates.

## Example: Preferring a Specific Worker Node

This configuration encourages the pod to run on any node labeled with `node-role.kubernetes.io/worker=worker` (e.g., our OCI worker), but allows it to run on the control plane if the worker is down.

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

Taints repel pods from nodes. A pod must have a matching `toleration` to be scheduled on a tainted node.

**Example Taint:**

```bash
kubectl taint nodes node1 key=value:NoSchedule
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

**Avoid pinning every application to a specific node.**

Adding `affinity` or `nodeSelector` to everything create rigid constraints that fight against Kubernetes' ability to self-heal.

### When to use Affinity

- **Hardware requirements:** The app needs a specific GPU, USB device, or architecture (ARM64 vs AMD64) present only on certain nodes.
- **Performance/cost:** Offload non-critical apps to a cheaper/slower node (like the OCI worker).
- **Data gravity:** Kubernetes handles this for you. If a pod uses a PVC on a specific node, Kubernetes naturally schedules the pod there.

### The "Filebrowser Lesson" (Anti-Pattern)

Do not force a pod to a node if it shares dependencies with other pods.

* **Scenario:** Filebrowser shared a volume with Jellyfin.
* **Constraint 1:** Jellyfin *must* run on `node-1` (GPU).
* **Constraint 2:** Filebrowser's volume is therefore locked to `node-1`.
* **Error:** Forcing Filebrowser to `node-2` caused a deadlock because the volume could not follow it.
* **Fix:** Remove the affinity. Let Kubernetes co-locate them naturally.
