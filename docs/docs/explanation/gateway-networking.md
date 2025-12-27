---
sidebar_position: 3
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
        TS["Tailscale Proxy Pod<br/>(gateway-envoy)"]
        SVC["LoadBalancer Service<br/>(ClusterIP: 10.x.x.x)"]
        ENVOY["Envoy Gateway<br/>(TLS Termination)"]
        APP["App Pod<br/>(e.g., docs, jellyfin)"]
    end

    subgraph External["External Services"]
        CF["Cloudflare DNS"]
        LE["Let's Encrypt"]
    end

    Client -->|"1. DNS: docs.sudhanva.me"| CF
    CF -->|"2. CNAME: gateway-envoy.*.ts.net"| Client
    Client -->|"3. TLS to 100.88.7.18:443"| TS
    TS -->|"4. DNAT to ClusterIP"| SVC
    SVC --> ENVOY
    ENVOY -->|"5. Route by hostname"| APP

    LE -.->|"ACME DNS-01"| CF
```

## Components

### Tailscale Operator

The Tailscale Kubernetes Operator creates proxy pods for `LoadBalancer` services when `spec.loadBalancerClass: tailscale` is set. Each proxy pod:

- Joins your Tailnet as a device (e.g., `gateway-envoy`)
- Gets a Tailscale IP (e.g., `100.88.7.18`)
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
- Pointing to the Tailscale hostname (`gateway-envoy.<tailnet>.ts.net`)

### cert-manager

cert-manager obtains wildcard TLS certificates from Let's Encrypt using DNS-01 challenges:

- The `ClusterIssuer` is configured with a Cloudflare API token
- A single `Certificate` resource covers `*.sudhanva.me`
- The certificate is stored in a Secret and referenced by the Gateway

## Traffic Flow

When you visit `https://docs.sudhanva.me` from your Mac:

- **DNS Resolution**: Your Tailscale client queries Tailscale DNS (100.100.100.100), which knows that `docs.sudhanva.me` points to `gateway-envoy.<tailnet>.ts.net`, which resolves to `100.88.7.18`.

- **TLS Connection**: Your browser connects to `100.88.7.18:443` via the WireGuard tunnel. The Tailscale proxy pod receives the connection.

- **DNAT**: iptables rules in the proxy pod rewrite the destination from `100.88.7.18:443` to the ClusterIP `10.x.x.x:443`.

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
| HTTPRoutes | `apps/*/httproute.yaml` | Per-app routing rules |

## Common Issues

### Cilium Socket LB Interference

When Cilium runs in kube-proxy replacement mode, its socket-level LoadBalancer intercepts connections in pod namespaces before iptables rules apply. This breaks the Tailscale proxy's DNAT.

**Fix:** Set `socketLB.hostNamespaceOnly=true` in Cilium. See [Cilium CNI](../tutorials/cilium.md).

### Missing SNI

Envoy requires Server Name Indication (SNI) to select the correct TLS certificate. If clients connect by IP without a hostname, Envoy logs `filter_chain_not_found`.

**Fix:** Always connect using the FQDN, not the Tailscale IP directly.
