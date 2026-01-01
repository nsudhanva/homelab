---
sidebar_position: 10
---

# Add an OCI Always Free worker

This guide provisions an OCI Always Free Ampere A1 worker VM, enrolls it in Tailscale, joins it to Kubernetes, and upgrades the control plane to match.

## Prerequisites

Step 1: Create an API signing key under Identity > Users > API Keys.

Step 2: Record the tenancy OCID, user OCID, and fingerprint from the OCI console.

Step 3: Ensure the target region is enabled for your tenancy.

Step 4: Create a Vault entry with a Tailscale auth key that is allowed to use `tag:k8s`.

Step 5: The module automatically selects the latest Ubuntu 24.04 ARM image.

## Provision the worker (Terraform)

Step 1: Copy `terraform/oci-worker/terraform.tfvars.example` to `terraform/oci-worker/terraform.tfvars`.

Step 2: Fill in tenancy, SSH key, region, AD, shape, and Tailscale auth key.

Step 3: From `terraform/oci-worker`, run `terraform init`.

Step 4: Run `terraform apply` and approve the plan.

Step 5: Record the public IP and the Tailscale IP once the node appears in the tailnet.

## Enroll the worker in Tailscale

Step 1: If the VM does not show up in the tailnet, SSH to the instance and install Tailscale manually:

```bash
ssh -i ~/.ssh/oci_worker ubuntu@<public-ip>
curl -fsSL https://tailscale.com/install.sh | sh
```

Step 2: Bring the node up with the tag:

```bash
sudo tailscale up --authkey "<auth-key>" --hostname oci-worker --accept-routes --advertise-tags tag:k8s
```

Step 3: If you see a tag permission error, update the Tailscale ACLs to allow the tag, then re-run the command.

Step 4: Update `ansible/inventory/oci-workers.yaml` with the Tailscale IP.

## Provision the worker with Ansible

Step 1: Run the CPU provisioning playbook against the OCI inventory:

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=ansible/roles \
ANSIBLE_PRIVATE_KEY_FILE=~/.ssh/oci_worker \
ansible-playbook -i ansible/inventory/oci-workers.yaml \
  ansible/playbooks/provision-cpu.yaml -e @ansible/group_vars/all.yaml \
  -e target_hosts=oci_workers
```

## Enable tailnet routing to the control plane

Step 1: On the control plane, advertise the LAN subnet so the OCI node can reach the API server:

```bash
sudo tailscale set --advertise-routes=192.168.0.0/24
```

Step 2: Approve the subnet route in the Tailscale admin console under the `legion` machine.

Step 3: From the OCI worker, confirm the control plane is reachable:

```bash
ping -c 2 192.168.0.133
```

## Join the worker to the cluster

Step 1: On the control plane, generate a join command:

```bash
sudo kubeadm token create --print-join-command
```

Step 2: Run the join command on the OCI worker:

```bash
sudo kubeadm join 192.168.0.133:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

Step 3: Confirm the node is Ready:

```bash
sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl get nodes -o wide
```

## Configure kubelet to use Tailscale IP

:::warning

The OCI worker registers with its VCN internal IP by default, which is not routable from the control plane LAN. You **must** configure kubelet to use the Tailscale IP as the node IP for pod networking to work.

:::

Step 1: Get the Tailscale IP on the OCI worker:

```bash
tailscale ip -4
```

Step 2: Update the kubelet args to use the Tailscale IP:

```bash
sudo sed -i 's/KUBELET_KUBEADM_ARGS=""/KUBELET_KUBEADM_ARGS="--node-ip=<TAILSCALE_IP>"/' /var/lib/kubelet/kubeadm-flags.env
```

Step 3: Restart kubelet:

```bash
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

Step 4: Verify the node IP changed in the cluster:

```bash
kubectl get nodes -o wide
```

The INTERNAL-IP column should now show the Tailscale IP (100.x.x.x) instead of the OCI VCN IP (10.42.x.x).

## Upgrade the control plane to match the worker

Step 1: Update the Kubernetes apt repository to `v1.35` on the control plane.

Step 2: Upgrade `kubeadm` and run the control plane upgrade:

```bash
sudo apt-get update
sudo apt-get install -y --allow-change-held-packages kubeadm
sudo kubeadm upgrade apply -y v1.35.0
```

Step 3: Upgrade `kubelet` and `kubectl`, then restart kubelet:

```bash
sudo apt-get install -y --allow-change-held-packages kubelet kubectl
sudo systemctl daemon-reload
sudo systemctl restart kubelet
```

Step 4: Re-check cluster health:

```bash
sudo KUBECONFIG=/etc/kubernetes/admin.conf kubectl get nodes -o wide
```

## Align the containerd sandbox image

Step 1: Ensure the control plane containerd config uses the repo default pause image:

```bash
sudo sed -i 's|sandbox_image = ".*"|sandbox_image = "registry.k8s.io/pause:3.10.1"|' /etc/containerd/config.toml
sudo systemctl restart containerd
```

## Notes

Step 1: For root compartment usage, set `compartment_ocid` to the tenancy OCID.

Step 2: The default domain OCID is not required for this flow.

## Troubleshooting & Lessons Learned

During the integration of the OCI worker and Tailscale-based networking, several critical issues were encountered. Here is a summary of the fixes and best practices:

### 1. External Traffic & Envoy Connectivity

**Issue:**  Accessing applications via the Gateway IP from the host machine failed with connection timeouts.
**Cause:**  The Envoy Gateway service defaulted to `externalTrafficPolicy: Local`. In a multi-node cluster connected via Tailscale (where the Envoy pod might be on a different node than the one receiving the traffic), "Local" policy drops traffic that doesn't terminate on the same node.
**Fix:**  Set `externalTrafficPolicy: Cluster` in the `EnvoyProxy` configuration. This allows traffic to be routed internally to the Envoy pod regardless of ingress node.

```yaml
# infrastructure/gateway/envoyproxy.yaml
spec:
  provider:
    kubernetes:
      envoyService:
        externalTrafficPolicy: Cluster
```

### 2. Tailscale Split DNS

**Issue:**  The host machine (Mac) failed to resolve internal domains like `*.sudhanva.me`, even though `nslookup` worked inside the cluster.
**Cause:**  The Mac was using the Tailscale `100.100.100.100` resolver, but Tailscale's control plane didn't have a specific "Split DNS" rule pointing the domain to the cluster's DNS service.
**Fix:**  In the **Tailscale Admin Console**, configure "Split DNS":

* **Domain:** `sudhanva.me`
* **Nameserver:** The Tailscale IP of the `tailscale-dns` service (e.g., `100.118.215.49`).

### 3. Stale DNS Configuration (GitOps)

**Issue:**  Manual fixes to the `tailscale-dns` ConfigMap (updating the Gateway IP) kept reverting.
**Cause:**  ArgoCD was syncing the cluster state from the git repository, which contained the old IP.
**Fix:**  Always commit configuration changes to the git repository. Source of truth must be Git.

### 4. Duplicate Tailscale Devices

**Issue:**  Re-provisioning nodes or restarting stateful workloads can create duplicate devices in Tailscale (e.g., `gateway-envoy` and `gateway-envoy-1`).
**Fix:**  Manually delete stale/offline devices from the Tailscale Admin Console to prevent routing confusion. Use persistent state storage for Tailscale pods if possible.

### 5. Node Roles

**Issue:**  The OCI worker showed `<none>` under ROLES.
**Fix:**  Manually label the node for clarity:

```bash
kubectl label node oci-worker node-role.kubernetes.io/worker=worker
```
