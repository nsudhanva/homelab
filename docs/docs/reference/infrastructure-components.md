---
sidebar_position: 4
title: Infrastructure Components
---

# Infrastructure Components

This page maps the infrastructure folders to their roles in the cluster.

## ArgoCD ApplicationSets

ApplicationSets watch `apps/` and `infrastructure/` and create ArgoCD Applications automatically.

- `bootstrap/templates/infra-appset.yaml`
- `bootstrap/templates/apps-appset.yaml`

## Core infrastructure

| Component | Path | Purpose | Notes |
| --- | --- | --- | --- |
| Gateway API CRDs | `infrastructure/gateway-api-crds/` | Installs Gateway API CRDs | Applied before Envoy Gateway |
| Envoy Gateway CRDs | `infrastructure/envoy-gateway-crds/` | Installs Envoy Gateway CRDs | Applied before Envoy Gateway |
| Envoy Gateway | `infrastructure/envoy-gateway/envoy-gateway.yaml` | Ingress controller for Gateway API | Helm chart with pinned image tag |
| Tailscale Operator | `infrastructure/tailscale/tailscale-operator.yaml` | Tailnet integration and LoadBalancer proxy pods | Requires `operator-oauth` Secret |
| cert-manager | `infrastructure/cert-manager/cert-manager.yaml` | TLS certificate management | Used with DNS-01 |
| ClusterIssuer | `infrastructure/cert-manager-issuer/cluster-issuer.yaml` | ACME issuer for wildcard certs | Update email and Cloudflare token |
| ExternalDNS | `infrastructure/external-dns/external-dns.yaml` | Creates DNS records for HTTPRoutes | Watches `external-dns.alpha.kubernetes.io/expose=true` |
| Gateway | `infrastructure/gateway/` | GatewayClass, Gateway, EnvoyProxy, cert | Uses Tailscale `gatewayClassName` |
| Longhorn | `bootstrap/templates/longhorn.yaml` | Storage via Longhorn | Helm chart in ArgoCD |
| GPU plugins | `infrastructure/gpu/` | Intel and NVIDIA device plugins | Optional, based on node hardware |

## Gateway and route definitions

Gateway resources are split by purpose:

- `infrastructure/gateway/gatewayclass.yaml`
- `infrastructure/gateway/gateway.yaml`
- `infrastructure/gateway/envoyproxy.yaml`
- `infrastructure/gateway/certificate.yaml`
- `infrastructure/gateway/argocd-httproute.yaml`
- `infrastructure/gateway/longhorn-httproute.yaml`

HTTPRoutes for apps live alongside each app under `apps/*/httproute.yaml`.
