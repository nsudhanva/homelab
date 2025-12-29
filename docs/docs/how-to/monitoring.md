---
sidebar_position: 11
title: Deploy Prometheus And Grafana
---

# Deploy Prometheus And Grafana

This guide installs the Prometheus stack with Grafana and Alertmanager, exposes them via the Tailscale Gateway, and wires Headlamp metrics into Prometheus.

## Step 1: Store Grafana admin credentials in Vault

Create the Vault KV entry that External Secrets will sync into the `grafana-admin` Secret.

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/monitoring/grafana-admin \
  admin-user="REPLACE_ME" \
  admin-password="REPLACE_ME"
```

## Step 2: Sync the Prometheus stack

ArgoCD will create the `monitoring` namespace and deploy the stack from `infrastructure/prometheus/`.

```bash
kubectl -n argocd get applications | rg prometheus
```

## Step 3: Access the dashboards

Open the following URLs on the tailnet:

- Grafana: `https://grafana.sudhanva.me`
- Prometheus: `https://prometheus.sudhanva.me`
- Alertmanager: `https://alertmanager.sudhanva.me`

## Step 4: Confirm Headlamp metrics

Headlamp exposes `/metrics` once `HEADLAMP_CONFIG_METRICS_ENABLED` is set. Prometheus discovers it via the ServiceMonitor in `apps/headlamp/servicemonitor.yaml`.

```bash
kubectl -n monitoring get servicemonitors
```
