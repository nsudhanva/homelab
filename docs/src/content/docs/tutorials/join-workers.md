---
title: Add Worker Nodes to K3s Cluster
description: The node scope of this K3s cluster. The cluster has one server node, and the repository has no automation for worker nodes.
keywords:
  - k3s worker node
  - add node to cluster
  - ansible k3s agent
  - kubernetes cluster expansion
  - multi-node k3s
sidebar:
  order: 8
---

# Add Workers

The cluster has one K3s server node, `legion`, and no worker nodes. The repository has no inventory group and no Ansible role for K3s agents, so the playbook cannot add a worker.
