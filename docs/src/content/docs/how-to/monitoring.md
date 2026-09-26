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

## Step 5: Telegram Alerting

Alertmanager sends alerts to the `alert-summarizer` service (`apps/alert-summarizer/`), which summarizes each alert with the local LLM and posts it to Telegram. Grafana posts to Telegram directly.

- Bot: `@ManassuHomelabBot`
- Target Chat ID: `7341944813`
- Secret storage: Bot token stored in Vault at `kv/telegram/bot`
- GitOps Secret Sync: ExternalSecret in `infrastructure/prometheus/external-secret-telegram.yaml` creates `alertmanager-telegram` in `monitoring`, which `alert-summarizer` mounts
- Alertmanager route: `prometheus.yaml` groups alerts by `alertname` and `namespace` (`group_wait: 30s`, `group_interval: 5m`, `repeat_interval: 1h`) and sends them to `http://alert-summarizer.monitoring.svc.cluster.local:8000/webhook` with `send_resolved: true`
- Silenced routes: `Watchdog`, `InfoInhibitor`, `Alertmanager*FailedToSendAlerts`, and `severity=info` go to the `null` receiver
- Grafana: Contact point `Telegram AlertBot` configured as default notification policy

### Alert summarizer behavior

- The webhook acknowledges Alertmanager immediately and processes alerts in the background, one at a time.
- Each alert is summarized into symptom, probable cause, and recommended action by `gemma-4-e2b-it` (`ALERT_LLM_TIMEOUT_SECONDS`, `ALERT_LLM_MAX_TOKENS`). If the model does not answer in time, a plain template message is sent instead.
- Re-deliveries of the same alert state (same fingerprint and status) within `ALERT_DEDUP_WINDOW_SECONDS` (default 3000 seconds) are skipped. The window is shorter than `repeat_interval`, so hourly reminders for alerts that are still firing are delivered.
- New images roll out automatically through Argo CD Image Updater (digest strategy).

To test the alerting pipeline, send a test alert payload to Alertmanager:

```bash
kubectl exec -n monitoring alertmanager-monitoring-alertmanager-0 -c alertmanager -- \
  wget -qO- --post-data='[{"labels":{"alertname":"TestTelegramAlert","severity":"info","instance":"k3s-cluster"},"annotations":{"summary":"Homelab Alerting Verified","description":"Telegram alerts delivered successfully."}}]' \
  --header='Content-Type: application/json' http://localhost:9093/api/v2/alerts
```
