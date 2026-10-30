---
title: Deploy and Manage Actual Budget with SimpleFIN Sync
description: Deploy Actual Budget with ArgoCD, keep its data on local-path storage, expose it through the Tailscale Gateway, and connect bank accounts through SimpleFIN Bridge.
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

This guide tells how the cluster deploys Actual Budget. It also tells how Actual Budget connects to bank feeds through SimpleFIN Bridge.

## Architecture and Layout

Actual Budget runs as one replica. It keeps its SQLite data on the local NVMe storage.

| Component | Resource | Purpose |
| --- | --- | --- |
| Manifest directory | `apps/actual-budget/` | The Kubernetes manifests |
| ArgoCD application | `app.yaml` | The `apps` ApplicationSet finds this file |
| Namespace | `namespace.yaml` | `actual-budget`, with the Pod Security Admission labels `audit` and `warn` at `baseline` |
| Local storage | `pvc.yaml` | The 5Gi `local-path` PersistentVolumeClaim `actual-budget-data`, mounted at `/data` |
| Server | `deployment.yaml` | `docker.io/actualbudget/actual-server:26.10.0-alpine`, run as a non-root user |
| Cluster network | `service.yaml` | A ClusterIP Service on port 5006 |
| Gateway route | `httproute.yaml` | A route on `tailscale-gateway` for `actual.sudhanva.me` |

:::note

Actual Budget needs HTTPS and cross-origin isolation (`SharedArrayBuffer` with `Cross-Origin-Opener-Policy` and `Cross-Origin-Embedder-Policy`). The Tailscale Gateway terminates TLS with the wildcard Let's Encrypt certificate. The browser then gives Actual Budget a secure context.

:::

## Step 1: Review the Kubernetes Manifests

The Deployment has these settings:

- Non-root user: The container runs as UID 1001 and GID 1001 (the `actual` user in Alpine).
- SQLite access: One replica with `strategy: Recreate` prevents SQLite file lock conflicts during upgrades.
- Health probes: The liveness, readiness, and startup probes use the `/health` HTTP endpoint.
- Resources: The requests are 100m CPU and 256Mi memory. The limits are 500m CPU and 512Mi memory.

## Step 2: Set the Server Password

Do these steps after ArgoCD syncs the application:

- Open `https://actual.sudhanva.me` in your browser. The setup wizard asks for a server password.
- Choose a strong password.
- Save the password in Vault at `kv/actual` (property `password`). The `actual-classifier` ExternalSecret and the Bitwarden script in Step 6 read this path.
- Create a budget file, or import a budget file.

## Step 3: Connect SimpleFIN Bank Sync

Actual Budget has built-in support for SimpleFIN Bridge. Do these steps to connect your banks:

- Step 3.1: Log in to the [SimpleFIN Bridge Dashboard](https://beta-bridge.simplefin.org/).
- Step 3.2: Make sure that your bank accounts are linked and show recent balances.
- Step 3.3: In the SimpleFIN dashboard, under Apps or Connections, click **Create Setup Token**.
- Step 3.4: Copy the one-time base64 token.
- Step 3.5: To keep a copy, store the token in Vault at `kv/actual-budget/simplefin` (property `setup_token`).
- Step 3.6: In Actual Budget, go to **Settings** &rarr; **Bank Sync**.
- Step 3.7: Under SimpleFIN, select **Set up**. Paste the setup token into the dialog.

Actual Budget validates the claim URL and claims a permanent access key. It encrypts the key in the server database on the persistent volume.

:::tip

A SimpleFIN setup token works one time only. If a claim expires or fails because of a network error, create a new setup token in the SimpleFIN Bridge dashboard.

:::

## Step 4: Link Accounts and Sync Transactions

Do these steps after you configure the SimpleFIN provider:

- Step 4.1: In the Actual Budget sidebar, click **Add Account**, or click an existing account.
- Step 4.2: Select **Link bank account**.
- Step 4.3: Select **SimpleFIN** as the provider.
- Step 4.4: Select the bank and the account from the list.
- Step 4.5: Click **Sync** at the top of the account ledger to import transactions. On a mobile device, pull down to refresh.

:::note

SimpleFIN Bridge gets data from the bank aggregators one time each day. A sync gets new transactions only after SimpleFIN refreshes its data.

:::

## Step 5: Back Up and Restore the Data

The budget data, the transaction history, the encryption keys, and the SimpleFIN connection secrets are in `/data`.

- Host path: `/home/k3s-storage/pvc-<uid>_actual-budget_actual-budget-data`. The base directory is `local_storage_path` in `ansible/group_vars/all.yaml`, and the name follows the default `local-path` pattern.
- Budget files: `/data/user-files/`
- Server credentials and SQLite database: `/data/server-files/account.sqlite`
- Restore: Copy the backup of `/data` to the new persistent volume.

## Step 6: Back Up the Credentials to Bitwarden

The script `scripts/sync-actual-budget-bw.sh` copies the Actual Budget credentials from Vault to Bitwarden. No ExternalSecret or cluster workload runs it. Run it from your workstation when the password or the SimpleFIN token changes.

The script reads these Vault paths through `kubectl -n vault exec vault-0`:

| Vault path | Property | Override variable |
| --- | --- | --- |
| `kv/actual` | `password` | `VAULT_AUTH_PATH` |
| `kv/actual-budget/simplefin` | `setup_token` | `VAULT_SIMPLEFIN_PATH` |

It creates two items in the Bitwarden folder that `BW_FOLDER_ID` sets. The script has a default folder ID.

- A login item named `Actual Budget (Homelab)`, with the username `admin`, the password from Vault, and the URL `https://actual.sudhanva.me`
- A secure note named `SimpleFIN Bridge Setup Token (Actual Budget)`, with the setup token

Step 6.1: Install `kubectl`, `jq`, and the Bitwarden CLI (`bw`). Log in with `bw login`.

Step 6.2: Export a Vault token. If Bitwarden is unlocked, also export `BW_SESSION`. If `BW_SESSION` is not set, the script runs `bw unlock`.

```bash
export VAULT_TOKEN="REPLACE_ME"
./scripts/sync-actual-budget-bw.sh
```

:::caution

The script creates new items on each run. It does not update existing items. After a run, delete the old items in Bitwarden to prevent duplicates.

:::
