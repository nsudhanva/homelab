---
title: Gateway API and Networking
---

# Gateway API and Networking

This document explains how traffic flows from your Tailnet clients to applications running in the cluster.

## Overview

The homelab uses a layered approach to expose HTTPS services:

```mermaid
flowchart TB
    subgraph Tailnet["Tailnet (Private Network)"]
        Client["Your Mac/Phone"]
    end

    subgraph Cluster["Kubernetes Cluster"]
        TS["Tailscale Proxy Pod (gateway-envoy)"]
        SVC["LoadBalancer Service (ClusterIP)"]
        ENVOY["Envoy Gateway (TLS Termination)"]
        APP["App Pod (e.g., docs, jellyfin)"]
    end

    subgraph External["External Services"]
        CF["Cloudflare DNS"]
        LE["Let's Encrypt"]
    end

    Client -->|"1. DNS: docs.sudhanva.me"| CF
    CF -->|"2. CNAME: gateway-envoy.TAILNET.ts.net"| Client
    Client -->|"3. TLS to TAILSCALE_GATEWAY_IP:443"| TS
    TS -->|"4. DNAT to ClusterIP"| SVC
    SVC --> ENVOY
    ENVOY -->|"5. Route by hostname"| APP

    LE -.->|"ACME DNS-01"| CF
```

## Detailed Request Path

```mermaid
sequenceDiagram
    participant Client as Tailnet Client
    participant TSdns as Tailscale DNS
    participant TS as Tailscale Proxy Pod
    participant Svc as Envoy Service (ClusterIP)
    participant Envoy as Envoy Gateway
    participant Route as HTTPRoute
    participant AppSvc as App Service
    participant Pod as App Pod

    Client->>TSdns: Query docs.sudhanva.me
    TSdns-->>Client: 100.x.y.z
    Client->>TS: TLS 443 to 100.x.y.z
    TS->>Svc: DNAT to ClusterIP:443
    Svc->>Envoy: Forward to Envoy Gateway
    Envoy->>Route: Match Host header + SNI
    Route->>AppSvc: Pick backend Service:80
    AppSvc->>Pod: Forward to Pod:8080
    Pod-->>Client: HTTP response
```

## Control Plane Objects and Ownership

```mermaid
flowchart LR
  subgraph DNS["DNS + TLS"]
    CF["Cloudflare DNS zone"]
    LE["Let's Encrypt"]
    Issuer["ClusterIssuer"]
    Cert["Certificate (wildcard)"]
  end

  subgraph Tailscale["Tailscale"]
    Operator["Tailscale Operator"]
    ProxySvc["Envoy Service (LoadBalancer class)"]
    ProxyPod["Proxy Pod (gateway-envoy)"]
  end

  subgraph Gateway["Gateway API"]
    GatewayClass["GatewayClass tailscale"]
    Gateway["Gateway tailscale-gateway"]
    EnvoyProxy["EnvoyProxy"]
    HTTPRoute["HTTPRoute (apps/*/httproute.yaml)"]
  end

  CF --> Issuer
  Issuer --> Cert
  Cert --> Gateway
  Operator --> ProxyPod
  ProxySvc --> ProxyPod
  EnvoyProxy --> ProxySvc
  GatewayClass --> Gateway
  Gateway --> HTTPRoute
  HTTPRoute --> ProxySvc
  LE -.-> CF
```

## Components

### Tailscale Operator

The Tailscale Kubernetes Operator creates proxy pods for `LoadBalancer` services when `spec.loadBalancerClass: tailscale` is set. Each proxy pod:

- Joins your Tailnet as a device (e.g., `gateway-envoy`)
- Gets a Tailscale IP (for example, `TAILSCALE_GATEWAY_IP`)
- Uses iptables DNAT to forward traffic to the Kubernetes ClusterIP

### Envoy Gateway

Envoy Gateway implements the Gateway API and handles:

- TLS termination using certificates from cert-manager
- SNI-based routing to select the correct filter chain
- HTTPRoute matching to forward requests to backend services

The `EnvoyProxy` resource configures the Envoy deployment as a `LoadBalancer` with `loadBalancerClass: tailscale`, which triggers the Tailscale Operator to create the proxy.

### ExternalDNS

ExternalDNS watches HTTPRoute resources with the annotation `external-dns.alpha.kubernetes.io/expose: "true"` and creates DNS records in Cloudflare:

- Subdomain CNAMEs (e.g., `docs.sudhanva.me`)
- Pointing to the Tailscale hostname (`gateway-envoy.TAILNET.ts.net`)

### cert-manager

cert-manager obtains wildcard TLS certificates from Let's Encrypt using DNS-01 challenges:

- The `ClusterIssuer` is configured with a Cloudflare API token
- A single `Certificate` resource covers `*.sudhanva.me`
- The certificate is stored in a Secret and referenced by the Gateway

## Required wiring for Tailnet ingress

These resources have to align or HTTPS routing through Tailscale will break:

- Cilium runs with `kubeProxyReplacement=true` and `socketLB.hostNamespaceOnly=true` so the Tailscale proxy DNAT works.
- EnvoyProxy exposes a `LoadBalancer` service with `loadBalancerClass: tailscale` and a stable Tailscale hostname.
- Gateway uses `gatewayClassName: tailscale` and points to the wildcard certificate.
- ExternalDNS targets the Tailscale hostname via the Gateway annotation.
- cert-manager creates the wildcard certificate in the `tailscale` namespace.
- HTTPRoutes live in app namespaces and include the ExternalDNS expose annotation.
- Cloudflare API tokens and Tailscale OAuth credentials are synced from Vault through External Secrets Operator.

## Split-horizon DNS for public hostnames

Some hostnames need different targets on and off the tailnet. For example, `docs.sudhanva.me` should resolve to the cluster on tailnet clients and to Cloudflare Pages for public clients.

To make this work:

- Keep the public Cloudflare DNS record pointing at Pages.
- Route tailnet DNS through the `tailscale-dns` resolver, which answers `*.sudhanva.me` with the Tailscale Gateway IP.
- Do not annotate the HTTPRoute with `external-dns.alpha.kubernetes.io/expose: "true"` so ExternalDNS does not overwrite the public record.
- The `tailscale-dns-updater` CronJob refreshes the Gateway IP in the resolver config.

## In-cluster access to Gateway services

Pods inside the cluster cannot route to Tailscale IPs (`100.x.x.x`). When a pod needs to reach a service exposed via the Tailscale Gateway (e.g., Vault for OIDC token exchange), DNS must resolve to an internal IP.

```mermaid
flowchart LR
    subgraph Cluster["Kubernetes Cluster"]
        Pod["App Pod (e.g., Headlamp)"]
        CoreDNS["CoreDNS"]
        GWInt["gateway-internal Service"]
        Envoy["Envoy Gateway"]
        Backend["Backend Service"]
    end

    Pod -->|"1. DNS: vault.sudhanva.me"| CoreDNS
    CoreDNS -->|"2. Rewrite to gateway-internal"| GWInt
    Pod -->|"3. HTTPS to ClusterIP:443"| GWInt
    GWInt --> Envoy
    Envoy -->|"4. Route by hostname"| Backend
```

CoreDNS rewrites `*.sudhanva.me` to the `gateway-internal` service:

```
sudhanva.me:53 {
    rewrite name regex (.*)\.sudhanva\.me gateway-internal.envoy-gateway.svc.cluster.local answer auto
    kubernetes cluster.local ...
}
```

The `gateway-internal` service selects Envoy pods by label, so it tracks the gateway dynamically:

```yaml
selector:
  gateway.envoyproxy.io/owning-gateway-name: tailscale-gateway
  gateway.envoyproxy.io/owning-gateway-namespace: tailscale
```

This enables pods to use the same hostnames as external clients while routing internally.

## Quick validation commands

Run these from any kubectl context that can reach the cluster:

```bash
kubectl get gatewayclass
kubectl get gateways -n tailscale
kubectl get envoyproxy -n tailscale
kubectl get svc -n tailscale
kubectl get certificates -n tailscale
kubectl get pods -n tailscale
kubectl get pods -n envoy-gateway
kubectl get httproute -A
```

For the Cilium requirement:

```bash
cilium config view | grep -E "bpf-lb-sock|kubeProxyReplacement"
```

## Traffic Flow

When you visit `https://docs.sudhanva.me` from your Mac:

- **DNS Resolution**: Your Tailscale client queries Tailscale DNS (100.100.100.100), which knows that `docs.sudhanva.me` points to `gateway-envoy.TAILNET.ts.net`, which resolves to `TAILSCALE_GATEWAY_IP`.

- **TLS Connection**: Your browser connects to `TAILSCALE_GATEWAY_IP:443` via the WireGuard tunnel. The Tailscale proxy pod receives the connection.

- **DNAT**: iptables rules in the proxy pod rewrite the destination from `TAILSCALE_GATEWAY_IP:443` to the ClusterIP `10.x.x.x:443`.

- **Cilium Processing**: With `socketLB.hostNamespaceOnly=true`, Cilium processes the DNAT'd packet at the tc layer (not socket layer) and routes it to the Envoy pod.

- **TLS Termination**: Envoy reads the SNI (`docs.sudhanva.me`) and selects the filter chain with the wildcard certificate.

- **HTTPRoute Matching**: Envoy matches the `Host` header to an HTTPRoute and forwards the request to the backend Service (e.g., `docs.docs.svc.cluster.local:80`).

## Key Configuration Files

| Component | Path | Purpose |
|-----------|------|---------|
| Gateway | `infrastructure/gateway/gateway.yaml` | Defines listeners and TLS |
| GatewayClass | `infrastructure/gateway/gatewayclass.yaml` | Links to EnvoyProxy |
| EnvoyProxy | `infrastructure/gateway/envoyproxy.yaml` | LoadBalancer + Tailscale |
| Certificate | `infrastructure/gateway/certificate.yaml` | Wildcard cert request |
| Internal Service | `infrastructure/gateway/internal-service.yaml` | In-cluster access to gateway |
| CoreDNS | `infrastructure/coredns/configmap.yaml` | Split-horizon DNS for pods |
| HTTPRoutes | `apps/*/httproute.yaml` | Per-app routing rules |

## Common Issues

### Cilium Socket LB Interference

When Cilium runs in kube-proxy replacement mode, its socket-level LoadBalancer intercepts connections in pod namespaces before iptables rules apply. This breaks the Tailscale proxy's DNAT.

**Fix:** Set `socketLB.hostNamespaceOnly=true` in Cilium. See [Cilium CNI](../tutorials/cilium.md).

### Missing SNI

Envoy requires Server Name Indication (SNI) to select the correct TLS certificate. If clients connect by IP without a hostname, Envoy logs `filter_chain_not_found`.

**Fix:** Always connect using the FQDN, not the Tailscale IP directly.

### Gateway shows not programmed

If `kubectl get gateways -n tailscale` reports `PROGRAMMED=False`, confirm:

- The GatewayClass points at `tailscale-proxy`.
- The EnvoyProxy service is `LoadBalancer` with `loadBalancerClass: tailscale`.
- The Tailscale Operator pod is running and can tag devices.

Reconcile by checking the Envoy Gateway controller logs:

```bash
kubectl logs -n envoy-gateway -l app.kubernetes.io/name=envoy-gateway --tail=200
```
