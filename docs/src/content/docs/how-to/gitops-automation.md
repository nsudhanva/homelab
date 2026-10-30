---
title: GitOps-Driven Infrastructure Automation
description: Run host provisioning from GitHub Actions over Tailscale, and upgrade K3s with the Rancher System Upgrade Controller.
keywords:
  - gitops automation
  - system upgrade controller
  - k3s automated upgrade
  - tailscale github action
  - ansible automation
sidebar:
  order: 17
---

# GitOps-Driven Infrastructure Automation

This repository runs host provisioning and K3s upgrades from Git. A push to `master` starts each process.

```mermaid
flowchart TD
  subgraph HostProv["GitOps Host Provisioning"]
    GitAnsible["Push to ansible/**"] --> GHA["GitHub Actions Runner"]
    GHA --> Tailnet["Tailscale Secure Mesh (tailscale/github-action)"]
    Tailnet --> LegionHost["Node 'legion' (100.66.139.118)"]
    LegionHost --> AnsibleRun["Runs ansible-playbook"]
  end

  subgraph ClusterUp["In-Cluster GitOps Upgrades"]
    GitK3s["Commit Plan CRD (infrastructure/system-upgrade-controller/)"] --> Argo["ArgoCD"]
    Argo --> SUC["System Upgrade Controller"]
    SUC --> K3sUpgrade["Upgrade K3s Binary, Restart Service (no cordon or drain)"]
  end
```

## Host Provisioning with GitHub Actions

When a push to `master` changes `ansible/**` or `.github/workflows/provision.yaml`, the `Ansible Provision` workflow runs `ansible-playbook -i ansible/inventory/hosts.yaml ansible/site.yaml`. The playbook applies the roles `common`, `tailscale`, `nvidia`, `k3s_server`, and `argocd`. Before you push, preview the node changes locally with `--check --diff`.

### Step 1: Review the Tailscale Connection

The workflow (`.github/workflows/provision.yaml`) uses `tailscale/github-action` with a Tailscale OAuth client. The runner joins the tailnet as an ephemeral `tag:ci` node. It connects to `legion` (`100.66.139.118`) through SSH.

`legion` runs Tailscale SSH. Tailscale SSH lets a tagged device connect only to tagged devices. For this reason, the policy in `terraform/tailscale/policy.hujson` has these items:

- The tags `tag:ci` and `tag:server`
- The tag `tag:server` on `legion`
- An SSH rule that accepts `tag:ci` to `tag:server` as the user `sudhanva`
- An `sshTests` entry that checks this rule on each policy change

Refer to [Manage Tailscale with Terraform](/how-to/tailscale-terraform/).

The OAuth client in the `TS_OAUTH_CLIENT_ID` and `TS_OAUTH_SECRET` secrets must have the `auth_keys` scope, so that it can create auth keys with `tag:ci`.

### Step 2: Add the Repository Secrets

Add these secrets to the GitHub repository (`Settings > Secrets and variables > Actions`):

- `TS_OAUTH_CLIENT_ID`: The Tailscale OAuth client ID.
- `TS_OAUTH_SECRET`: The Tailscale OAuth client secret.
- `SSH_PRIVATE_KEY`: An SSH private key whose public key is in `~/.ssh/authorized_keys` for `sudhanva` on `legion`.

### Step 3: Start the Provisioning

Provisioning starts automatically when a push to `master` changes `ansible/**` or the workflow file. To start it manually, click **Run workflow** in GitHub Actions (`workflow_dispatch`).

## K3s Upgrades with the System Upgrade Controller

The cluster runs the Rancher System Upgrade Controller `v0.20.2`. `infrastructure/system-upgrade-controller/kustomization.yaml` does these tasks:

- It pulls the upstream release manifests `crd.yaml` and `system-upgrade-controller.yaml`.
- It adds `k3s-upgrade-plan.yaml`.
- It sets the kubectl Job image to `rancher/kubectl:v1.36.2`.
- It adds resource requests and limits to the controller.

### Step 1: Set the Target K3s Version

To upgrade K3s, edit `infrastructure/system-upgrade-controller/k3s-upgrade-plan.yaml` in Git:

```yaml
apiVersion: upgrade.cattle.io/v1
kind: Plan
metadata:
  name: k3s-server
  namespace: system-upgrade
spec:
  concurrency: 1
  version: v1.37.1+k3s1
  nodeSelector:
    matchExpressions:
      - key: node-role.kubernetes.io/control-plane
        operator: Exists
  serviceAccountName: system-upgrade
  tolerations:
    - key: CriticalAddonsOnly
      operator: Exists
    - key: node-role.kubernetes.io/control-plane
      operator: Exists
      effect: NoSchedule
  cordon: false
  upgrade:
    image: rancher/k3s-upgrade
```

### Step 2: Push to Git

Commit and push the change. ArgoCD syncs the `Plan` resource to the cluster.

### Step 3: Let the Controller Upgrade K3s

The System Upgrade Controller finds the new version and starts an upgrade Job on the control-plane node. The Plan sets `cordon: false` and has no `drain` block, so the controller does not cordon or drain the node. The Job runs the `rancher/k3s-upgrade` container. This container replaces the K3s binary and restarts the `k3s` service. The pods continue to run during the restart.
