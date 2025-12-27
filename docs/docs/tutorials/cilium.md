---
sidebar_position: 5
title: Cilium CNI
---

# Cilium CNI

## Step 1: Install Cilium

```bash
CILIUM_VERSION=$(grep -E "cilium_version:" ansible/group_vars/all.yaml | head -n 1 | awk -F'\"' '{print $2}')
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}
cilium install --version $CILIUM_VERSION --set kubeProxyReplacement=true
kubectl -n kube-system delete daemonset kube-proxy
cilium hubble enable --ui
kubectl get nodes
cilium status
```
