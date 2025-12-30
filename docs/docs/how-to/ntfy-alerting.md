---
sidebar_position: 12
title: Ntfy Alerting
---

# Ntfy Alerting

This guide deploys a self-hosted ntfy server, wires Alertmanager into ntfy via a webhook adapter, and adds alert rules for pod crashes and node resource pressure.

## Step 1: Sync ntfy and the alert adapter

ArgoCD will deploy ntfy from `infrastructure/ntfy/` and the alert adapter plus rules from `infrastructure/ntfy-alerts/`.

```bash
kubectl -n argocd get applications | rg ntfy
```

## Step 2: Subscribe to the alerts topic

Open the ntfy UI and subscribe to the `alerts` topic from the mobile app.

- URL: `https://ntfy.sudhanva.me`

## Step 3: Validate alert routing

Open Alertmanager and confirm that alerts with `alert_channel="ntfy"` appear in the UI.

- URL: `https://alertmanager.sudhanva.me`

## Step 4: Verify delivery

Trigger a test alert by creating a crashing pod or temporarily lowering the alert thresholds, then confirm the ntfy notification arrives.

## Notes

Current rules alert on pod crash loops, frequent restarts, failed pods, node CPU/memory/disk usage above 90%, and nodes that are not Ready.
