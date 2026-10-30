---
title: Ubuntu Workstation Container
description: Run an Ubuntu 26.04 workstation in Apple Containers with Docker, Ansible, and kubectl installed for cluster administration.
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

The workstation container gives you an Ubuntu 26.04 shell with Docker, Ansible, and kubectl. It runs on macOS hosts that have the Apple `container` CLI (`brew install container`). Use it when a workflow needs Linux tools.

## Step 1: Start the container

```bash
./scripts/dev-container.sh up
```

The script starts a container named `homelab-dev` from `docker.io/library/ubuntu:26.04` with 4 CPUs and 8G of memory. Set `DEV_CPUS` and `DEV_MEMORY` to change these values. The script then installs `docker.io`, `ansible`, and `kubectl` `v1.37.1`, and starts `dockerd` inside the container.

## Step 2: Open a shell

```bash
./scripts/dev-container.sh shell
```

## Step 3: Confirm the tooling

```bash
docker info --format '{{.ServerVersion}}'
ansible --version
kubectl version --client
```

## Step 4: Work on the repo from inside

The container mounts the repo root at `/homelab`, and `shell` opens in that directory. Thus your edits apply directly to your checkout. Run Ansible playbooks and cluster scripts from the mounted path.

## Step 5: Stop the container

```bash
./scripts/dev-container.sh down
```

`down` stops and deletes the container. The tools install again on the next `up`. All state stays in the repo checkout on the host.
