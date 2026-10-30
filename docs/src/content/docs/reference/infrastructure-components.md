---
title: Infrastructure Components Reference
description: A reference of all infrastructure components that ArgoCD manages, with their configuration paths. It includes networking, storage, secrets, monitoring, and security tools.
keywords:
  - kubernetes infrastructure components
  - argocd applications
  - flannel cni
  - local-path storage
  - vault secrets
  - prometheus monitoring
  - cert-manager
  - external dns
  - envoy gateway
sidebar:
  order: 1
---

# Infrastructure Components

This page shows the function of each infrastructure folder in the cluster.

```mermaid
flowchart TB
  subgraph Git["Git repo folders"]
    Boot["bootstrap/"]
    Infra["infrastructure/"]
    Apps["apps/"]
  end

  subgraph Argo["ArgoCD"]
    AppSetInfra["ApplicationSet infra"]
    AppSetApps["ApplicationSet apps"]
    InfraApps["infra-* apps"]
    UserApps["app-* apps"]
  end

  subgraph Cluster["Cluster namespaces"]
    Tailscale["tailscale"]
    Envoy["envoy-gateway"]
    Cert["cert-manager"]
    ExtDNS["external-dns"]
    ExtSecrets["external-secrets"]
    Vault["vault"]
    Monitoring["monitoring"]
  end

  Boot --> AppSetInfra
  Boot --> AppSetApps
  Infra --> InfraApps
  Apps --> UserApps
  AppSetInfra --> InfraApps
  AppSetApps --> UserApps
  InfraApps --> Tailscale
  InfraApps --> Envoy
  InfraApps --> Cert
  InfraApps --> ExtDNS
  InfraApps --> ExtSecrets
  InfraApps --> Vault
  InfraApps --> Monitoring
```

## ArgoCD ApplicationSets

ApplicationSets watch `apps/` and `infrastructure/` and automatically create ArgoCD Applications. These files define them:

- `bootstrap/templates/infra-appset.yaml`
- `bootstrap/templates/apps-appset.yaml`

## Core infrastructure

K3s provides the Local-Path Provisioner itself (StorageClass `local-path`). It is not an `infrastructure/` component.

| Component | Path | Purpose | Notes |
| --- | --- | --- | --- |
| ArgoCD | `bootstrap/argocd/` | GitOps controller install (`v3.5.6`) | The `argocd` Ansible role applies it. Not managed by an ApplicationSet |
| ArgoCD Image Updater | `infrastructure/argocd-image-updater/` | Automated image updates | Uses the ImageUpdater CRD and the `argocd-image-updater-registries` Secret from Vault |
| Gateway API CRDs | `infrastructure/gateway-api-crds/gateway-api-crds.yaml` | Installs Gateway API CRDs and the safe-upgrades ValidatingAdmissionPolicy | ArgoCD pulls upstream `config/crd` at `v1.6.3` |
| Envoy Gateway CRDs | `infrastructure/envoy-gateway-crds/` | Installs Envoy Gateway CRDs | Kustomize pulls the upstream `v1.9.2` CRD bundle |
| Envoy Gateway | `infrastructure/envoy-gateway/envoy-gateway.yaml` | Ingress controller for Gateway API | Helm chart `v1.9.2` with image `v1.9.2`. Bundled CRDs are off (`crds.enabled: false`) |
| Tailscale Operator | `infrastructure/tailscale/tailscale-operator.yaml` | Tailnet integration and LoadBalancer proxy pods | Needs the `operator-oauth` Secret, which an ExternalSecret creates from Vault |
| cert-manager | `infrastructure/cert-manager/cert-manager.yaml` | TLS certificate management | Used with DNS-01 |
| ClusterIssuer | `infrastructure/cert-manager-issuer/cluster-issuer.yaml` | ACME issuer for wildcard certs | Cloudflare API token solver |
| ExternalDNS | `infrastructure/external-dns/external-dns.yaml` | Creates DNS records for HTTPRoutes | Watches `external-dns.alpha.kubernetes.io/expose=true` |
| CoreDNS override | `infrastructure/coredns/configmap.yaml` | Rewrites `*.sudhanva.me` to `gateway-internal` | Split-horizon DNS for in-cluster access |
| Tailscale DNS | `infrastructure/tailscale-dns/` | Split-horizon DNS for tailnet clients: HTTPRoute hosts go to the Gateway, other names to public DNS | CoreDNS exposed through a Tailscale LoadBalancer |
| External Secrets CRDs | `infrastructure/external-secrets-crds/` | Installs External Secrets CRDs | Kustomize pulls upstream CRD bundle |
| External Secrets Operator | `infrastructure/external-secrets/external-secrets.yaml` | Syncs secrets from Vault | ClusterSecretStore and ExternalSecret manifests |
| Gateway | `infrastructure/gateway/` | GatewayClass, Gateway, EnvoyProxy, cert, internal-service | Uses Tailscale `gatewayClassName` |
| Vault | `infrastructure/vault/vault.yaml` | Central secrets storage | PVC on local-path |
| Prometheus Operator CRDs | `infrastructure/prometheus-operator-crds/` | Prometheus CRDs | Installed before the monitoring stack |
| Prometheus stack | `infrastructure/prometheus/` | Metrics, alerting, dashboards | Grafana, Prometheus, Alertmanager, and HTTPRoutes |
| Kubescape | `infrastructure/kubescape/` | Cluster security scanning | Operator runs in offline mode |
| Metrics Server | `infrastructure/metrics-server/` | CPU and memory metrics API | Necessary for the Headlamp usage graphs |
| GPU Operator | `infrastructure/gpu/` | NVIDIA GPU Operator | Helm chart `v26.7.2` with Container Device Interface (CDI) as the default |
| System Upgrade Controller | `infrastructure/system-upgrade-controller/` | Automated K3s cluster upgrades | Kustomize pulls the upstream `v0.20.2` manifests and adds the `k3s-server` Plan |

## Gateway and route definitions

Each gateway and route resource has its own file:

- `infrastructure/gateway/gatewayclass.yaml`
- `infrastructure/gateway/gateway.yaml`
- `infrastructure/gateway/envoyproxy.yaml`
- `infrastructure/gateway/certificate.yaml`
- `infrastructure/gateway/internal-service.yaml`
- `infrastructure/gateway/argocd-httproute.yaml`
- `infrastructure/gateway/vault-httproute.yaml`
- `infrastructure/prometheus/httproute-grafana.yaml`
- `infrastructure/prometheus/httproute-prometheus.yaml`
- `infrastructure/prometheus/httproute-alertmanager.yaml`
