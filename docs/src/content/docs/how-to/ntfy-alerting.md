---
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

Trigger a test alert and confirm the ntfy notification arrives.

```bash
curl -sS -XPOST -H 'Content-Type: application/json' https://alertmanager.sudhanva.me/api/v2/alerts -d '[{"labels":{"alertname":"HomelabTestAlert","severity":"info","alert_channel":"ntfy"},"annotations":{"summary":"Test alert from CLI"},"generatorURL":"https://homelab.local/test"}]'
```

```bash
curl -sS 'https://ntfy.sudhanva.me/alerts/json?poll=1' | head -n 5
```

## Troubleshooting

### Ntfy cache database corruption

If the ntfy logs show `database disk image is malformed`, clear the cache database and restart the deployment.

Step 1: Pause ArgoCD auto-sync for the ntfy app if it keeps recreating the pod.

Step 2: Scale the ntfy deployment to zero and wait for the pod to terminate.

Step 3: Delete `/var/cache/ntfy/cache.db` from the ntfy pod or a debug pod that mounts the `ntfy-cache` PVC.

Step 4: Scale back to one replica and re-enable auto-sync.

Step 5: Re-run the test alert in Step 4.

If deleting `cache.db` returns an I/O error, detach the Longhorn volume and run `fsck` on the node before starting the pod again.

## Notes

Current rules alert on pod crash loops, frequent restarts, failed pods, node CPU/memory/disk usage above 90%, and nodes that are not Ready.
