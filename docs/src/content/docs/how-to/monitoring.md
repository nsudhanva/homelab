---
title: Deploy Prometheus, Grafana, and Alertmanager
description: Install the Prometheus monitoring stack with Grafana dashboards and Alertmanager. Configure ServiceMonitors for application metrics and expose the dashboards through Tailscale Gateway.
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

This guide installs the Prometheus stack with Grafana and Alertmanager. It exposes them through the Tailscale Gateway and connects the Headlamp metrics to Prometheus.

## Step 1: Store Grafana admin credentials in Vault

Create the Vault KV entry. External Secrets syncs this entry into the `grafana-admin` Secret.

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/monitoring/grafana-admin \
  admin-user="REPLACE_ME" \
  admin-password="REPLACE_ME"
```

## Step 2: Sync the Prometheus stack

ArgoCD creates the `monitoring` namespace and installs the Prometheus Operator CRDs. Then it deploys the stack from `infrastructure/prometheus/`.

```bash
kubectl -n argocd get applications | rg prometheus
```

## Step 3: Access the dashboards

Open these URLs on the tailnet.

- Grafana: `https://grafana.sudhanva.me`
- Prometheus: `https://prometheus.sudhanva.me`
- Alertmanager: `https://alertmanager.sudhanva.me`

## Step 4: Confirm Headlamp metrics

Headlamp exposes `/metrics` when `HEADLAMP_CONFIG_METRICS_ENABLED` is set. Prometheus finds the endpoint through the ServiceMonitor in `apps/headlamp/servicemonitor.yaml`.

```bash
kubectl -n monitoring get servicemonitors
```

## Step 5: Telegram Alerting

Alertmanager sends alerts to the `alert-summarizer` service (`apps/alert-summarizer/`). This service uses the local LLM to summarize each alert and posts the summary to Telegram. Grafana posts to Telegram directly.

- Bot: `@ManassuHomelabBot`
- Target Chat ID: `7341944813`
- Secret storage: Vault keeps the bot token at `kv/telegram/bot`
- GitOps Secret Sync: The ExternalSecret in `infrastructure/prometheus/external-secret-telegram.yaml` creates `alertmanager-telegram` in `monitoring`. The `alert-summarizer` service mounts this Secret
- Alertmanager route: `prometheus.yaml` groups alerts by `alertname` and `namespace` (`group_wait: 30s`, `group_interval: 5m`, `repeat_interval: 1h`). It sends them to `http://alert-summarizer.monitoring.svc.cluster.local:8000/webhook` with `send_resolved: true`
- Silenced routes: `Watchdog`, `InfoInhibitor`, `Alertmanager*FailedToSendAlerts`, and `severity=info` go to the `null` receiver
- Grafana: The contact point `Telegram AlertBot` is the default notification policy

### Alert summarizer behavior

- The webhook acknowledges Alertmanager immediately. Then it processes the alerts in the background, one at a time.
- The shared `homelab-ai` model chain writes a summary of each alert with a symptom, a probable cause, and a recommended action. The Deployment limits the output with `AI_MAX_TOKENS` and `AI_TEMPERATURE`. If no model answers, the service sends a plain template message.
- The service ignores a repeated delivery of the same alert state (same fingerprint and status) in the `ALERT_DEDUP_WINDOW_SECONDS` window (default 3000 seconds). This window is shorter than `repeat_interval`. Thus the service still sends hourly reminders for alerts that continue to fire.
- Argo CD Image Updater deploys new images automatically (digest strategy).

To test the alert pipeline, send a test alert payload to Alertmanager.

```bash
kubectl exec -n monitoring alertmanager-monitoring-alertmanager-0 -c alertmanager -- \
  wget -qO- --post-data='[{"labels":{"alertname":"TestTelegramAlert","severity":"info","instance":"k3s-cluster"},"annotations":{"summary":"Homelab Alerting Verified","description":"Telegram alerts delivered successfully."}}]' \
  --header='Content-Type: application/json' http://localhost:9093/api/v2/alerts
```
