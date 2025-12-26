---
sidebar_position: 7
title: Verify Ansible Roles with Multipass
---

# Verify Ansible Roles with Multipass

This guide runs the Ansible provisioning playbook against a Multipass VM to validate the roles on a systemd host with real kernel and networking behavior.

## Prerequisites

- Multipass installed on your workstation
- Ansible installed on your workstation
- A dedicated SSH key at `~/.ssh/homelab-multipass.pub`

## Step: Create a dedicated SSH key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/homelab-multipass -N ""
```

## Step: Launch a test VM

```bash
multipass launch --name ansible-test --cpus 2 --memory 4G --disk 20G 24.04
```

## Step: Add your SSH key

```bash
multipass exec ansible-test -- bash -c "mkdir -p /home/ubuntu/.ssh && cat >> /home/ubuntu/.ssh/authorized_keys" < ~/.ssh/homelab-multipass.pub
```

## Step: Create a temporary inventory

```bash
cat <<'EOF' > /tmp/ansible-multipass-test.yaml
all:
  children:
    k8s_nodes:
      hosts:
        ansible-test:
          ansible_host: 192.168.2.200
          ansible_user: ubuntu
EOF
```

Replace the IP address with the one shown in `multipass list`.

## Step: Run the playbook

```bash
ANSIBLE_HOST_KEY_CHECKING=False ANSIBLE_ROLES_PATH=ansible/roles \
ANSIBLE_PRIVATE_KEY_FILE=~/.ssh/homelab-multipass \
ansible-playbook -i /tmp/ansible-multipass-test.yaml \
  ansible/playbooks/provision-cpu.yaml \
  -e @ansible/group_vars/all.yaml
```

## Step: Clean up the VM

```bash
multipass delete ansible-test
multipass purge
```
