---
sidebar_position: 6
title: Maintenance
---

# Maintenance

:::note

These steps target bare metal clusters. For local VM testing, use [Local Multipass Cluster](../tutorials/local-multipass-cluster.md).

:::

## Adding Nodes to the Cluster

This section covers expanding the cluster with additional worker nodes or control plane nodes.

:::note

You can also add nodes by updating `ansible/inventory/hosts.yaml` and rerunning `ansible-playbook ansible/playbooks/provision-cpu.yaml`.

:::

### Prerequisites for New Nodes

Use Ansible to prepare new nodes so the baseline is consistent across the cluster.

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-cpu.yaml
```

### For Nodes with GPUs

Use the GPU-specific playbooks to enable the runtime and device plugins:

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-nvidia-gpu.yaml
```

```bash
ansible-playbook -i ansible/inventory/hosts.yaml \
  ansible/playbooks/provision-intel-gpu.yaml
```

### Generate Join Token (On Existing Control Plane)

Tokens expire after 24 hours. Run this on an existing control plane node to generate a new join command:

```bash
kubeadm token create --print-join-command
```

### Add a Worker Node

Run the join command from above on the new worker node:

```bash
sudo kubeadm join <control-plane-ip>:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

### Add a Control Plane Node (HA Setup)

:::warning

For HA control planes, you need a load balancer in front of all control planes and must initialize the first control plane with `--control-plane-endpoint=<load-balancer-ip>:6443`.

:::

Generate a certificate key on an existing control plane:

```bash
sudo kubeadm init phase upload-certs --upload-certs
```

Then join with the `--control-plane` flag:

```bash
sudo kubeadm join <load-balancer-ip>:6443 \
  --token <token> \
  --discovery-token-ca-cert-hash sha256:<hash> \
  --control-plane \
  --certificate-key <certificate-key>
```

After joining, configure kubectl on the new control plane:

```bash
mkdir -p $HOME/.kube
sudo cp -i /etc/kubernetes/admin.conf $HOME/.kube/config
sudo chown $(id -u):$(id -g) $HOME/.kube/config
```

## Routine checks

Use these checks if the cluster runs unattended for long periods.

```bash
kubectl get nodes
kubectl get pods -A
kubectl get apps -n argocd
```

## Namespace migration

Use this flow to move existing apps out of the `default` namespace.

### Step 1: Add a namespace and update manifests

Create `apps/<app-name>/namespace.yaml` and `apps/<app-name>/app.yaml`, then update every manifest in the app folder to use `namespace: <app-name>`. If two apps must share storage, point both `app.yaml` files at the same namespace.

### Step 2: Let ArgoCD sync

Once the changes are pushed, ArgoCD will reconcile the app into the new namespace.

### Step 3: Remove old resources

After the new namespace is healthy, delete the old resources in `default` to avoid conflicts.

```bash
kubectl delete deployment,service,httproute -n default -l app=<app-name>
```

If the app owns PVCs, plan a data migration before deleting the old claims.

## Node maintenance window

Use this flow to patch or reboot a node safely.

### Step 1: Drain the node

```bash
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```

### Step 2: Apply OS updates or reboot

Perform the host maintenance, then confirm the node is back online.

### Step 3: Uncordon the node

```bash
kubectl uncordon <node-name>
```

## Upgrade Kubernetes (Bare Metal)

Upgrade control plane nodes first, then upgrade workers.

:::note

Check the latest stable Kubernetes release before setting `k8s_version` and `TARGET_VERSION`.

:::

### Step 1: Update versions and packages

Update `k8s_version` in `ansible/group_vars/all.yaml`, then run the provisioning playbook against all nodes.

### Step 2: Upgrade the control plane

Run these on each control plane node, one at a time:

```bash
sudo kubeadm upgrade plan
TARGET_VERSION="v1.35.x"
sudo kubeadm upgrade apply ${TARGET_VERSION}
sudo apt-get install -y kubelet kubeadm kubectl
sudo systemctl restart kubelet
```

Replace `v1.35.x` with the target patch version after checking the latest stable release.

### Step 3: Upgrade each worker node

Drain, upgrade, then uncordon each worker:

```bash
kubectl drain <worker-name> --ignore-daemonsets --delete-emptydir-data
sudo kubeadm upgrade node
sudo apt-get install -y kubelet kubeadm kubectl
sudo systemctl restart kubelet
kubectl uncordon <worker-name>
```

### Step 4: Verify the upgrade

```bash
kubectl get nodes
kubectl get pods -A
```

## Version Management (Ansible + ArgoCD)

Use this flow to keep every node consistent while maintaining HA.

### Step 1: Update the pinned versions

Host-level versions are pinned in `ansible/group_vars/all.yaml`:

- `k8s_version` for kubeadm/kubelet/kubectl
- `containerd_version` for the container runtime
- `cilium_version` for the CNI

Cluster-level components (Longhorn, Tailscale, Envoy Gateway, cert-manager, ExternalDNS, ArgoCD) are pinned in their ArgoCD templates or manifests:

- `bootstrap/templates/longhorn.yaml`
- `infrastructure/tailscale/tailscale-operator.yaml`
- `infrastructure/envoy-gateway/envoy-gateway.yaml`
- `infrastructure/envoy-gateway-crds/`
- `infrastructure/gateway-api-crds/`
- `infrastructure/cert-manager/cert-manager.yaml`
- `infrastructure/external-dns/external-dns.yaml`
- `infrastructure/external-secrets-crds/`
- `bootstrap/templates/*-appset.yaml` for repo references

### Step 2: Apply the change consistently

- **Host packages** (Kubernetes, containerd): rerun the provisioning playbook on all nodes so every host converges to the same version.
- **Cluster add-ons** (Cilium, Longhorn, ArgoCD): update the version in Git and let ArgoCD sync. For Cilium, use `cilium upgrade` after updating `cilium_version`.

### Step 3: Keep HA during updates

- Upgrade control planes one at a time, then workers.
- Drain nodes before upgrades and uncordon after, as described in the Kubernetes upgrade steps above.
- Verify health between nodes: `kubectl get nodes` and `kubectl get pods -A`.

## Upgrade Cilium

Update `cilium_version` in `ansible/group_vars/all.yaml`, then run:

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'\"' '{print $2}')
cilium upgrade --version ${CILIUM_VERSION}
cilium status --wait
```

## Upgrade ArgoCD

```bash
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
```

## Upgrade Longhorn

Update `targetRevision` in `bootstrap/templates/longhorn.yaml`, then let ArgoCD sync the application.

## Recreate From Scratch (Ubuntu 24.04)

Use this section when rebuilding a node from bare metal or VM images:

### Base setup

Install Ubuntu 24.04 LTS and log in as a user with sudo. Clone this repo and review the pinned versions and paths in `ansible/group_vars/all.yaml`.

### Automated setup

Run the Ansible provisioning playbook, then continue at [Kubernetes](../tutorials/kubernetes.md).

### Manual setup

Follow the bare metal tutorial path in order, starting with [Prerequisites](../tutorials/prerequisites.md).

If you are rebuilding with existing data disks for Longhorn, ensure the storage path in `bootstrap/templates/longhorn.yaml` points to the correct mount before applying `bootstrap/root.yaml`.
