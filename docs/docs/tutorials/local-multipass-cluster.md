---
sidebar_position: 7
title: Local Multipass Cluster
---

# Local Multipass Cluster

This tutorial runs a multi-node Kubernetes cluster on local VMs using Multipass. The shape mirrors the bare-metal setup with one control plane and two workers while keeping systemd, kernel modules, and networking closer to real hardware than Docker-based simulation.

## Prerequisites

- Multipass installed on your workstation
- Ansible installed on your workstation
- kubectl installed on your workstation
- A dedicated SSH key stored in the repository
- At least 12GB of free RAM

## Step: Install host tools

macOS (Homebrew):

```bash
brew install --cask multipass
brew install ansible kubectl
```

Ubuntu 24.04 (Snap + APT):

```bash
sudo snap install multipass
sudo apt-get update
sudo apt-get install -y ansible
sudo snap install kubectl --classic
```

## Step: Create a dedicated SSH key

```bash
mkdir -p ansible/.keys
ssh-keygen -t ed25519 -f ansible/.keys/multipass -N ""
```

This key is only used for the local Multipass VMs and keeps your personal SSH identities out of the workflow.

## Step: Launch the VMs with static IPs

Use cloud-init to assign fixed IPs so the Ansible inventory does not change between runs. Update the gateway and subnet to match your host network.

```bash
cat <<'EOF' > /tmp/homelab-cp-cloudinit.yaml
network:
  version: 2
  ethernets:
    primary:
      match:
        name: "en*"
      set-name: eth0
      addresses: [192.168.2.2/24]
      gateway4: 192.168.2.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
EOF

cat <<'EOF' > /tmp/homelab-w1-cloudinit.yaml
network:
  version: 2
  ethernets:
    primary:
      match:
        name: "en*"
      set-name: eth0
      addresses: [192.168.2.3/24]
      gateway4: 192.168.2.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
EOF

cat <<'EOF' > /tmp/homelab-w2-cloudinit.yaml
network:
  version: 2
  ethernets:
    primary:
      match:
        name: "en*"
      set-name: eth0
      addresses: [192.168.2.4/24]
      gateway4: 192.168.2.1
      nameservers:
        addresses: [1.1.1.1, 8.8.8.8]
EOF
```

```bash
multipass launch --name homelab-cp --cpus 2 --memory 4G --disk 20G --cloud-init /tmp/homelab-cp-cloudinit.yaml 24.04
multipass launch --name homelab-w1 --cpus 2 --memory 4G --disk 20G --cloud-init /tmp/homelab-w1-cloudinit.yaml 24.04
multipass launch --name homelab-w2 --cpus 2 --memory 4G --disk 20G --cloud-init /tmp/homelab-w2-cloudinit.yaml 24.04
```

## Step: Add the project SSH key to each VM

```bash
for node in homelab-cp homelab-w1 homelab-w2; do
  multipass exec "$node" -- bash -c "mkdir -p /home/ubuntu/.ssh && cat >> /home/ubuntu/.ssh/authorized_keys" < ansible/.keys/multipass.pub
done
```

## Step: Confirm VM IPs

```bash
multipass list
```

If you did not use static IPs, update `ansible/inventory/multipass.yaml` to match the VM IPs from the output.

## Step: Run Ansible provisioning

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=ansible/roles \
ANSIBLE_PRIVATE_KEY_FILE=ansible/.keys/multipass \
ansible-playbook -i ansible/inventory/multipass.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml
```

## Step: Initialize the control plane

```bash
multipass exec homelab-cp -- sudo kubeadm init --pod-network-cidr=10.244.0.0/16
```

## Step: Join the workers

```bash
JOIN_CMD=$(multipass exec homelab-cp -- sudo kubeadm token create --print-join-command)
multipass exec homelab-w1 -- bash -lc "sudo ${JOIN_CMD}"
multipass exec homelab-w2 -- bash -lc "sudo ${JOIN_CMD}"
```

## Step: Copy kubeconfig to your workstation

```bash
multipass exec homelab-cp -- sudo cp /etc/kubernetes/admin.conf /home/ubuntu/admin.conf
multipass exec homelab-cp -- sudo chown ubuntu:ubuntu /home/ubuntu/admin.conf
multipass transfer homelab-cp:/home/ubuntu/admin.conf /tmp/homelab-admin.conf
```

## Step: Install Cilium

Use the same Cilium version listed in `README.md` to stay aligned with the bare-metal setup.

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'\"' '{print $2}')
```

Install the Cilium CLI inside the control plane VM to avoid host architecture mismatches:

```bash
multipass exec homelab-cp -- bash -lc "CILIUM_CLI_VERSION=\$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt) \
  && ARCH=\$(uname -m) \
  && if [ \"\${ARCH}\" = \"aarch64\" ]; then CILIUM_ARCH=arm64; else CILIUM_ARCH=amd64; fi \
  && curl -L --fail --remote-name-all https://github.com/cilium/cilium-cli/releases/download/\${CILIUM_CLI_VERSION}/cilium-linux-\${CILIUM_ARCH}.tar.gz{,.sha256sum} \
  && sha256sum --check cilium-linux-\${CILIUM_ARCH}.tar.gz.sha256sum \
  && sudo tar xzvfC cilium-linux-\${CILIUM_ARCH}.tar.gz /usr/local/bin \
  && rm cilium-linux-\${CILIUM_ARCH}.tar.gz cilium-linux-\${CILIUM_ARCH}.tar.gz.sha256sum"
```

Then install Cilium from the VM:

```bash
multipass exec homelab-cp -- sudo cilium install --kubeconfig /etc/kubernetes/admin.conf --version ${CILIUM_VERSION} --set kubeProxyReplacement=true
multipass exec homelab-cp -- sudo kubectl --kubeconfig /etc/kubernetes/admin.conf -n kube-system delete daemonset kube-proxy
multipass exec homelab-cp -- sudo cilium status --kubeconfig /etc/kubernetes/admin.conf --wait
```

## Step: Verify nodes and run the smoke test

```bash
kubectl --kubeconfig /tmp/homelab-admin.conf get nodes -o wide
kubectl --kubeconfig /tmp/homelab-admin.conf apply -f ansible/tests/local-cluster/test-nginx/deployment.yaml
kubectl --kubeconfig /tmp/homelab-admin.conf apply -f ansible/tests/local-cluster/test-nginx/service.yaml
kubectl --kubeconfig /tmp/homelab-admin.conf get pods -l app=test-nginx
kubectl --kubeconfig /tmp/homelab-admin.conf get svc test-nginx
```

## Step: Tear down the cluster

```bash
multipass delete homelab-cp homelab-w1 homelab-w2
multipass purge
```

## Next: Move to bare metal

When you are ready for real hardware, follow the bare metal tutorial path in [Prerequisites](./prerequisites.md) and [System Preparation](./system-prep.md). The Ansible roles and GitOps layout stay the same, and only the inventory and host environment change.
