---
sidebar_position: 7
---

# ArgoCD & GitOps

## Phase 6: Install ArgoCD

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl wait --for=condition=available --timeout=600s deployment/argocd-server -n argocd
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d; echo
```

> [!NOTE]
> ArgoCD is exposed via Tailscale Ingress in `infrastructure/argocd-ingress/ingress.yaml` (hostname: `argocd`).

## Phase 10: GitOps Activation

### Update Repository URLs

Edit these files and replace `YOUR_USERNAME` with your GitHub username:
- `bootstrap/root.yaml`
- `bootstrap/templates/infra-appset.yaml`
- `bootstrap/templates/apps-appset.yaml`

Confirm the Longhorn data path in `bootstrap/templates/longhorn.yaml` matches your host.

### Apply Bootstrap

```bash
kubectl apply -f bootstrap/root.yaml
```

### Apply Longhorn (special handling)

> [!NOTE]
> Longhorn is deployed as a separate ArgoCD Application because it uses Helm and needs to be in the `argocd` namespace.

```bash
kubectl apply -f bootstrap/longhorn.yaml
```

### Verify Deployment

```bash
kubectl get apps -n argocd
```
