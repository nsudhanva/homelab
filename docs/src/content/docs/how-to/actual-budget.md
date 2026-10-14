---
title: Deploy and Manage Actual Budget with SimpleFIN Sync
description: Deploy Actual Budget on Kubernetes with ArgoCD GitOps, keep its state on local-path storage, expose it through Tailscale Gateway HTTPS, and link bank accounts with SimpleFIN Bridge.
keywords:
  - actual budget kubernetes
  - simplefin actual budget
  - actual budget gitops
  - actual budget argocd
  - personal finance homelab
  - bank sync actual budget
sidebar:
  order: 8
---

# Actual Budget with SimpleFIN

This guide tells how this homelab deploys and secures Actual Budget. It also tells how Actual Budget connects to bank feeds through SimpleFIN Bridge.

## Architecture & Layout

Actual Budget runs as a single-replica workload. It keeps its SQLite data on the fast local NVMe storage pool.

| Component | Resource | Purpose |
| --- | --- | --- |
| Manifest directory | `apps/actual-budget/` | All declarative Kubernetes specifications |
| ArgoCD application | `app.yaml` | Discovered by the `apps` ApplicationSet |
| Dedicated namespace | `namespace.yaml` | `actual-budget` with baseline Pod Security Admission |
| Local storage | `pvc.yaml` | 5Gi persistent volume claim mounted at `/data` |
| Core server | `deployment.yaml` | `actualbudget/actual-server:26.9.0-alpine` with non-root security |
| Cluster network | `service.yaml` | Internal ClusterIP exposing port 5006 |
| Gateway ingress | `httproute.yaml` | Route attached to `tailscale-gateway` at `actual.sudhanva.me` |

:::note

Actual Budget needs HTTPS and secure origin isolation (`SharedArrayBuffer` with `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy`). The Tailscale Gateway does the SSL termination with the wildcard Let's Encrypt certificate. This meets all browser cryptographic requirements.

:::

## Step 1: Understand the Kubernetes Manifests

The deployment follows the GitOps standards.

- Non-root user: The container runs as UID 1001 and GID 1001 (the `actual` user in Alpine)
- Persistent SQLite access: One replica with `strategy: Recreate` prevents SQLite file locking conflicts during upgrades
- Native health probes: The liveness, readiness, and startup probes use the built-in `/health` HTTP endpoint
- Resource limits: The requests are 100m CPU / 256Mi RAM. The limits are 500m CPU / 512Mi RAM

## Step 2: First-Time Initialization and Password Setup

After ArgoCD completes the sync of the application, do these steps.

- Open your browser and go to `https://actual.sudhanva.me`
- The bootstrap wizard opens and asks for a master server password
- Choose a strong password. Save it in your password manager or in Vault
- Create your primary budget file, or import a budget file that you have

## Step 3: Integrate SimpleFIN Bank Sync

Actual Budget has native support for SimpleFIN Bridge. Do these steps to connect your financial institutions.

- Step 3.1: Log in to your [SimpleFIN Bridge Dashboard](https://beta-bridge.simplefin.org/)
- Step 3.2: Make sure that your bank accounts are linked and show recent account balances
- Step 3.3: In the SimpleFIN dashboard, under Apps or Connections, click **Create Setup Token**
- Step 3.4: Copy the one-time base64 token string
- Step 3.5: In the Actual Budget web interface, go to **Settings** &rarr; **Bank Sync**
- Step 3.6: Under SimpleFIN, select **Set up**. Paste the setup token into the modal
- Step 3.7: Actual Budget validates the claim URL and claims your permanent access key. It encrypts the key in the server database on the persistent volume

:::tip

SimpleFIN setup tokens are single-use. If a token claim expires or has a network error, make a new setup token in the SimpleFIN Bridge dashboard.

:::

## Step 4: Link Accounts and Synchronize Transactions

After you configure the SimpleFIN provider, do these steps.

- Step 4.1: In the Actual Budget sidebar, click **Add Account** or click an account that you have
- Step 4.2: Select **Link bank account**
- Step 4.3: Choose **SimpleFIN** from the provider selection
- Step 4.4: Select the related financial institution and account from the dropdown list
- Step 4.5: To import transactions, click **Sync** at the top of the account ledger (or pull down to refresh on mobile devices)

:::note

SimpleFIN Bridge gets financial data from banking aggregators one time each day. If you sync many times each day, you get newly settled transactions when SimpleFIN refreshes them.

:::

## Step 5: Backup & Disaster Recovery

All budget data, transaction history, encryption keys, and SimpleFIN connection secrets are in `/data` on the host.

- Path on host: `/home/k3s-storage/actual-budget-actual-budget-data-*`
- Budget files: `/data/user-files/`
- Server credentials & SQLite db: `/data/server-files/account.sqlite`
- To restore from a backup, copy the contents of the `/data` directory to the restored persistent volume
