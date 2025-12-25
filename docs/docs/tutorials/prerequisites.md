---
sidebar_position: 2
---

# Prerequisites

## Phase 0: Prerequisites

```bash
sudo apt update
sudo add-apt-repository ppa:quentiumyt/nvtop
sudo apt install -y curl wget git pre-commit python3 python3-dev htop nvtop dmsetup npm nodejs
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install -y helm
```

## Phase 0b: Optional Ansible Provisioning

> [!NOTE]
> The Ansible playbooks are the automated equivalent of Phases 1-3. If you use Ansible, skip straight to Phase 4.

### Configure Inventory and Variables

Update the node list and user in `ansible/inventory/hosts.yaml`, then confirm versions and paths in `ansible/group_vars/all.yaml`.

### Run the Playbook

```bash
cd ansible
ansible-playbook playbooks/site.yaml
```
