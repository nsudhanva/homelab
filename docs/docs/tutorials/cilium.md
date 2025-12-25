---
sidebar_position: 6
---

# Cilium CNI

## Phase 5: Install Cilium

```bash
CILIUM_VERSION="1.18.5"
CILIUM_CLI_VERSION=$(curl -s https://raw.githubusercontent.com/cilium/cilium-cli/main/stable.txt)
curl -L --fail --remote-name-all \
  https://github.com/cilium/cilium-cli/releases/download/${CILIUM_CLI_VERSION}/cilium-linux-amd64.tar.gz{,.sha256sum}
sha256sum --check cilium-linux-amd64.tar.gz.sha256sum
sudo tar xzvfC cilium-linux-amd64.tar.gz /usr/local/bin
rm cilium-linux-amd64.tar.gz{,.sha256sum}
cilium install --version $CILIUM_VERSION --set kubeProxyReplacement=true
cilium hubble enable --ui
kubectl get nodes
cilium status
```

> [!NOTE]
> Keep `CILIUM_VERSION` aligned with `ansible/group_vars/all.yaml`.
