---
sidebar_position: 8
---

# Tailscale

## Phase 7: Tailscale Setup

### Install Tailscale Client

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

### Create OAuth Secret

Get OAuth credentials from https://login.tailscale.com/admin/settings/oauth (create with `devices:write` scope and tag `tag:k8s`).

```bash
kubectl create namespace tailscale
kubectl create secret generic operator-oauth \
  --namespace tailscale \
  --from-literal=client_id=YOUR_CLIENT_ID \
  --from-literal=client_secret=YOUR_CLIENT_SECRET
```

> [!IMPORTANT]
> Create the `operator-oauth` secret before Phase 10 so the Tailscale Operator deploys cleanly.

### Enable SSH for Remote Access

```bash
sudo apt-get install -y openssh-server
sudo systemctl enable --now ssh
```

### Remote kubectl Access

From another Tailnet device, SSH and run kubectl:

```bash
ssh user@<tailscale-hostname> kubectl get pods -A
```

Or copy kubeconfig to your other machine:

```bash
mkdir -p ~/.kube
scp user@<tailscale-hostname>:~/.kube/config ~/.kube/config
sed -i 's|server: https://.*:6443|server: https://<tailscale-hostname>:6443|' ~/.kube/config
kubectl get pods -A
```
