---
title: Ubuntu Workstation Container
description: Run an Ubuntu 26.04 workstation in Apple Containers with Docker, Ansible, and Kubernetes tooling preinstalled for cluster administration.
keywords:
  - ubuntu workstation container
  - apple containers ubuntu
  - linux dev container
  - docker in apple container
  - ansible workstation
sidebar:
  order: 10
---

# Ubuntu Workstation

The workstation container gives you an Ubuntu 26.04 shell with Docker, Ansible, kubectl, and Helm on any host that runs Apple Containers. Use it whenever a workflow expects Linux tooling.

## Step 1: Start the container

```bash
./scripts/dev-container.sh up
```

The script pulls `ubuntu:26.04`, allocates CPUs and memory, and prepares the container for nested Docker.

## Step 2: Open a shell

```bash
./scripts/dev-container.sh shell
```

## Step 3: Confirm the tooling

```bash
docker info --format '{{.ServerVersion}}'
ansible --version
kubectl version --client
helm version
```

## Step 4: Work on the repo from inside

The repo root is mounted into the container, so edits apply directly to your checkout. Run Ansible playbooks and cluster scripts from the mounted path.

## Step 5: Stop the container

```bash
./scripts/dev-container.sh down
```

The container is stateless by design. Tooling reinstalls on the next `up`, and all state lives in the repo checkout on the host.
