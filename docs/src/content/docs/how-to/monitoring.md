---
title: Deploy Prometheus, Grafana, and Alertmanager
description: Install the Prometheus monitoring stack with Grafana dashboards and Alertmanager. Configure ServiceMonitors for application metrics and expose dashboards via Tailscale Gateway.
keywords:
  - prometheus kubernetes
  - grafana kubernetes
  - alertmanager setup
  - kubernetes monitoring
  - prometheus operator
  - servicemonitor
  - kube-prometheus-stack
  - kubernetes metrics
sidebar:
  order: 10
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

ArgoCD will create the `monitoring` namespace, install the Prometheus Operator CRDs, and deploy the stack from `infrastructure/prometheus/`.

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
