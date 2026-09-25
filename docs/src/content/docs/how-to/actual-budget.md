---
title: Deploy and Manage Actual Budget with SimpleFIN Sync
description: Deploy Actual Budget personal finance system on Kubernetes via ArgoCD GitOps, persist state on local-path storage, expose via Tailscale Gateway HTTPS, and link bank accounts using SimpleFIN Bridge.
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

This guide explains how Actual Budget is deployed, secured, and connected to bank feeds via SimpleFIN Bridge in this homelab.

## Architecture & Layout

Actual Budget runs as a single-replica workload backed by SQLite storage on the high-speed local NVMe storage pool.

| Component | Resource | Purpose |
| --- | --- | --- |
| Manifest directory | `apps/actual-budget/` | Complete declarative Kubernetes specifications |
| ArgoCD application | `app.yaml` | Discovered by the `apps` ApplicationSet |
| Dedicated namespace | `namespace.yaml` | `actual-budget` with baseline Pod Security Admission |
| Local storage | `pvc.yaml` | 5Gi persistent volume claim mounted at `/data` |
| Core server | `deployment.yaml` | `actualbudget/actual-server:26.9.0-alpine` with non-root security |
| Cluster network | `service.yaml` | Internal ClusterIP exposing port 5006 |
| Gateway ingress | `httproute.yaml` | Route attached to `tailscale-gateway` at `actual.sudhanva.me` |

:::note

Actual Budget requires HTTPS and secure origin isolation (`SharedArrayBuffer` with `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy`). The Tailscale Gateway handles SSL termination using the wildcard Let's Encrypt certificate, satisfying all browser cryptographic requirements.

:::

## Step 1: Understand the Kubernetes Manifests

The deployment adheres strictly to GitOps standards:

- Non-root user: Runs under UID 1001 and GID 1001 (`actual` user in Alpine)
- Persistent SQLite access: Single-replica with `strategy: Recreate` guarantees zero SQLite file locking conflicts during upgrades
- Native health probes: Liveness, readiness, and startup probes target the built-in `/health` HTTP endpoint
- Resource limits: Requests 100m CPU / 256Mi RAM; limits set to 500m CPU / 512Mi RAM

## Step 2: First-Time Initialization and Password Setup

When the application finishes syncing in ArgoCD:

- Open your browser and navigate to `https://actual.sudhanva.me`
- You will be greeted by the initial bootstrap wizard prompting you to set a master server password
- Choose a strong password and save it in your password manager or Vault
- Create your primary budget file or import an existing budget file

## Step 3: Integrate SimpleFIN Bank Sync

Actual Budget includes direct native support for SimpleFIN Bridge. Follow these steps to connect your financial institutions:

- Step 3.1: Log in to your [SimpleFIN Bridge Dashboard](https://beta-bridge.simplefin.org/)
- Step 3.2: Verify your bank accounts are linked and displaying recent account balances
- Step 3.3: In the SimpleFIN dashboard under Apps or Connections, click **Create Setup Token**
- Step 3.4: Copy the generated one-time base64 token string
- Step 3.5: In the Actual Budget web interface, navigate to **Settings** &rarr; **Bank Sync**
- Step 3.6: Under SimpleFIN, select **Set up** and paste the setup token into the modal
- Step 3.7: Actual Budget validates the claim URL, claims your permanent access key, and encrypts the key inside the server's database on the persistent volume

:::tip

SimpleFIN setup tokens are single-use. If a token claim expires or encounters an initial network hiccup, generate a fresh setup token from the SimpleFIN Bridge dashboard.

:::

## Step 4: Link Accounts and Synchronize Transactions

Once the SimpleFIN provider is configured:

- Step 4.1: In Actual Budget's sidebar, click **Add Account** or click on an existing account
- Step 4.2: Select **Link bank account**
- Step 4.3: Choose **SimpleFIN** from the provider selection
- Step 4.4: Select the corresponding financial institution and account from the dropdown list
- Step 4.5: Click **Sync** at the top of the account ledger (or pull down to refresh on mobile devices) to import transactions

:::note

SimpleFIN Bridge updates financial data once per day from banking aggregators. Syncing multiple times a day fetches newly settled transactions whenever SimpleFIN refreshes them.

:::

## Step 5: Backup & Disaster Recovery

The entire budget data, transaction history, encryption keys, and SimpleFIN connection secrets live in `/data` on the host:

- Path on host: `/home/k3s-storage/actual-budget-actual-budget-data-*`
- Budget files: Stored in `/data/user-files/`
- Server credentials & SQLite db: Stored in `/data/server-files/account.sqlite`
- Restoring from backup simply requires copying the `/data` directory contents to the restored persistent volume
