---
title: Tailscale Ingress and Split-Horizon DNS
description: Configure the Tailscale Gateway API for Kubernetes ingress. Configure split-horizon DNS, ExternalDNS, and cert-manager wildcard certificates for custom domains.
keywords:
  - tailscale kubernetes
  - tailscale gateway api
  - split horizon dns
  - kubernetes ingress tailscale
  - tailscale operator
  - externaldns cloudflare
  - cert-manager dns01
  - tailscale oauth
sidebar:
  order: 9
---

# Tailscale

## Step 1: Set up Tailscale

### Install Tailscale Client

Install Tailscale on each node with the official install script, and join the node to your tailnet:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
```

The `tailscale` Ansible role fails if Tailscale is not installed. It does not install Tailscale for you.

### Tag owners

The operator and every proxy that it creates use `tag:k8s`. `operatorConfig.defaultTags` in `infrastructure/tailscale/tailscale-operator.yaml` sets the operator tag, and the `tailscale.com/tags: tag:k8s` annotations on the Envoy proxy and the `tailscale-dns` Service set the proxy tags. The tailnet policy in `terraform/tailscale/policy.hujson` makes `tag:k8s-operator` the owner of `tag:k8s`. Change tag owners there, not in the admin console. Refer to [Manage Tailscale with Terraform](/how-to/tailscale-terraform/).

### Store the OAuth credentials in Vault

Create an OAuth client at `https://login.tailscale.com/admin/settings/oauth`. Give it write access to devices and auth keys, and the tag `tag:k8s`. Then put the credentials in Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/operator-oauth client_id=YOUR_CLIENT_ID client_secret=YOUR_CLIENT_SECRET
```

The ExternalSecret `infrastructure/external-secrets/external-secret-tailscale-operator.yaml` creates the `operator-oauth` Secret in the `tailscale` namespace from `kv/tailscale/operator-oauth` (properties `client_id` and `client_secret`). The operator chart reads that Secret. Do not create the Secret with `kubectl`. Until Vault has the values, the Tailscale Operator cannot start, and the Gateway gets no Tailscale address. Set up Vault first with the [Vault guide](/how-to/vault/).

### Enable SSH for Remote Access

```bash
sudo apt-get install -y openssh-server
sudo systemctl enable --now ssh
```

### Remote kubectl Access

The provisioning playbook writes the kubeconfig to `k3s.kubeconfig` in the repo root on your workstation. It sets the server address to `https://<ansible_host>:6443`, which is the Tailscale IP of `legion`. Any tailnet device with a copy of that file can run kubectl:

```bash
export KUBECONFIG=$PWD/k3s.kubeconfig
kubectl get pods -A
```

The API server certificate covers the names in `tls_sans` in `ansible/group_vars/all.yaml`, so you can also use `legion` or its MagicDNS name as the server address.

### Node DNS

Cluster nodes do not use Tailscale DNS. The `tailscale` Ansible role runs `tailscale set --accept-dns=false` on each node. Thus, the host resolves names through its uplink resolvers. Image pulls and other node DNS lookups do not depend on DNS services in the cluster. Refer to [Node Networking and DNS](/explanation/node-networking/).

### Tailnet nameservers

`terraform/tailscale/dns.tf` sets the tailnet DNS. It looks up the Tailscale IPs of the operator proxies by hostname:

- Global nameservers: the Tailscale IP of `technitium-dns`, and AdGuard DNS (`94.140.14.14`, `94.140.15.15`) as the fallback
- Split DNS: `sudhanva.me` to the Tailscale IP of `tailscale-dns` (refer to [Split DNS resolver IP](#split-dns-resolver-ip))
- MagicDNS on, and local DNS settings overridden

AdGuard DNS keeps tailnet DNS working when the cluster is down. It blocks ads like Technitium does, because Tailscale queries all global nameservers at the same time. Refer to [Change the fallback nameservers](/how-to/tailscale-terraform/#change-the-fallback-nameservers).

## Step 2: Enable custom domains with Gateway API

This repo uses Envoy Gateway, ExternalDNS, and cert-manager with the Tailscale Gateway API. Subdomains such as `homelab.sudhanva.me` resolve to the Tailscale Gateway. A different system manages the apex `sudhanva.me`.

:::note

ExternalDNS creates only the subdomain records that you annotate. These records point to the Tailscale hostname. Thus, only tailnet clients can reach them.

:::

### Store the Cloudflare API token in Vault

In Cloudflare, create a token with DNS edit permissions for the `sudhanva.me` zone. Write it to Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/external-dns/cloudflare api-token=YOUR_CLOUDFLARE_API_TOKEN
kubectl -n vault exec -it vault-0 -- vault kv put kv/cert-manager/cloudflare api-token=YOUR_CLOUDFLARE_API_TOKEN
```

ExternalSecrets in `infrastructure/external-secrets/` create a Secret named `cloudflare-api-token` (key `api-token`) in three namespaces:

- `external-dns`, from `kv/external-dns/cloudflare` (`external-secret-cloudflare-external-dns.yaml`)
- `cert-manager`, from `kv/cert-manager/cloudflare` (`external-secret-cloudflare-cert-manager.yaml`)
- `tailscale`, from `kv/cert-manager/cloudflare` (`external-secret-cloudflare-cert-manager-tailscale.yaml`)

Do not create these Secrets with `kubectl`.

:::note

If your cluster uses split-horizon DNS for `*.sudhanva.me`, configure cert-manager to use public recursive resolvers. This repo sets these flags in `infrastructure/cert-manager/cert-manager.yaml`:

```bash
--dns01-recursive-nameservers=1.1.1.1:53,1.0.0.1:53
--dns01-recursive-nameservers-only=true
```

:::

### Update the ACME email

Before you sync, set your email in `infrastructure/cert-manager-issuer/cluster-issuer.yaml`.

### Set the Tailscale Gateway target

The `external-dns.alpha.kubernetes.io/target` annotation in `infrastructure/gateway/gateway.yaml` sets the CNAME target for ExternalDNS records. The repo value is `gateway-envoy-1.ainu-herring.ts.net`, the MagicDNS name of the Envoy proxy device in the tailnet. The `tailscale.com/hostname: gateway-envoy` annotation in `infrastructure/gateway/envoyproxy.yaml` requests the hostname. Tailscale adds the `-1` suffix when the name is already taken. If you rebuild the tailnet device, compare the device name in the Tailscale admin console with this annotation and update it in Git.

### Split DNS resolver IP

The split DNS resolver for `sudhanva.me` must point to the `tailscale-dns` service IP. Do not point it to the Gateway IP. The `tailscale-dns` resolver answers HTTPRoute hostnames with the Gateway IP. If split DNS points directly to the Gateway IP, queries time out.

The resolver runs in the `tailscale-dns` namespace. It does not run in the `tailscale` namespace.

To get the resolver IP, run:

```bash
kubectl -n tailscale-dns get svc tailscale-dns -o wide
```

To examine the answer from the resolver, get the Gateway IP:

```bash
kubectl get gateway -n tailscale tailscale-gateway -o jsonpath='{.status.addresses[*].value}' && echo
```

Compare the `IPAddress` value with the output of `dig +short <name> @100.100.100.100`.

### Hosts outside the homelab

The `tailscale-dns` resolver answers with the Gateway IP only for hostnames that an HTTPRoute serves. Every other `sudhanva.me` name, such as the apex, `www`, `google` or `lakshmi.k8s`, goes to public DNS, so sites hosted elsewhere stay reachable from the tailnet.

The `tailscale-dns-updater` CronJob builds that list every 10 minutes. It reads the HTTPRoute hostnames and writes them into the `match` regex of the `template` block:

```text
template IN A {
    match "^(grafana|argocd|...)[.]sudhanva[.]me[.]$"
    answer "{{ .Name }} 60 IN A <gateway IP>"
    fallthrough
}
```

A new HTTPRoute resolves on the tailnet within 10 minutes. To apply it at once, start a Job from the CronJob:

```bash
kubectl -n tailscale-dns create job --from=cronjob/tailscale-dns-updater tailscale-dns-updater-now
```

## Split-horizon DNS for homelab.sudhanva.me

The docs hostnames `homelab.sudhanva.me` and `docs.sudhanva.me` have manual public A records that point to the Tailscale Gateway IP. ExternalDNS does not manage them, because their HTTPRoute has no `external-dns.alpha.kubernetes.io/expose` annotation. Tailnet clients reach the cluster through the Tailscale Gateway. Clients off the tailnet cannot reach these hostnames. They can use the Cloudflare Pages copy at `homelab-68o.pages.dev`.

Keep the manual public records. The split-DNS resolver below answers the same hostnames for tailnet clients.

### Deploy the split-DNS resolver

This repo has a CoreDNS deployment that answers HTTPRoute hostnames with the Tailscale Gateway IP. It forwards all other `sudhanva.me` names to public DNS. A CronJob keeps the IP and the hostname list the same as the cluster. Refer to [Hosts outside the homelab](#hosts-outside-the-homelab).

Sync the `infrastructure/tailscale-dns/` component. Then get the Tailscale IP of the resolver:

```bash
kubectl -n tailscale-dns get svc tailscale-dns -o wide
```

To examine the updater, look at the `tailscale-dns-updater` CronJob and the logs of its latest Job.

### Configure Cloudflare (public)

In the `sudhanva.me` zone, set `homelab.sudhanva.me` to the public hostname.

### Tailscale DNS (tailnet)

The `split_dns` block in `terraform/tailscale/dns.tf` sends `sudhanva.me` to the Tailscale IP of `tailscale-dns`, not the Gateway IP.

### macOS resolver fallback

If `dig` works but browsers or CLI tools cannot resolve `*.sudhanva.me`, add a resolver file. This file makes macOS send `sudhanva.me` queries to Tailscale:

```bash
sudo mkdir -p /etc/resolver
echo "nameserver 100.100.100.100" | sudo tee /etc/resolver/sudhanva.me
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

### Keep ExternalDNS from overriding public DNS

The docs HTTPRoute does not have the ExternalDNS expose annotation. Thus, ExternalDNS does not overwrite the public record.

### Verify split-horizon behavior

On a tailnet device, run:

```bash
dig +short homelab.sudhanva.me @100.100.100.100
curl -I https://homelab.sudhanva.me
```

Expected results:

- DNS resolves to the Tailscale Gateway IP (the `status.addresses` value of `tailscale-gateway`).
- The response headers do not include Cloudflare headers such as `cf-ray`.

On a device that is not on the tailnet, run:

```bash
dig +short homelab.sudhanva.me @1.1.1.1
curl -I https://homelab.sudhanva.me
```

Expected results:

- DNS resolves to Cloudflare IPs.
- The response headers include `server: cloudflare`.

### Troubleshooting

If tailnet queries continue to go to Cloudflare, do these steps:

- Turn Tailscale off and then on again to refresh the DNS settings.
- Flush the macOS DNS cache:

```bash
sudo dscacheutil -flushcache
sudo killall -HUP mDNSResponder
```

## Troubleshooting

### Connections to subdomains time out

If `tailscale ping <gateway-ip>` works but `curl https://subdomain.sudhanva.me` times out, examine the Tailscale ingress proxy pod. Make sure that it is running and healthy:

```bash
kubectl get pods -n tailscale -l tailscale.com/parent-resource-type=svc
```

If the proxy pod needs a refresh, restart it:

```bash
kubectl delete pod -n tailscale -l tailscale.com/parent-resource-type=svc
```

Make sure that the Envoy Gateway data plane pod is running and accepts traffic on port 10443:

```bash
kubectl get pods -n envoy-gateway
```

### Envoy returns "filter_chain_not_found"

This error in the Envoy logs means that the TLS connection has no Server Name Indication (SNI). Make sure that:

- Clients connect with the hostname (for example, `homelab.sudhanva.me`), not an IP address
- The hostname matches a configured HTTPRoute
- The certificate covers the requested hostname (examine it with `kubectl get certificate -n tailscale`)

### DNS not resolving

If subdomains do not resolve, examine these items:

- ExternalDNS logs: `kubectl logs -n external-dns -l app.kubernetes.io/instance=external-dns`
- The Cloudflare API token has DNS edit permissions
- The HTTPRoute has the `external-dns.alpha.kubernetes.io/expose: "true"` annotation

### Verify the traffic flow

```bash
# Check Gateway is programmed
kubectl get gateways -n tailscale

# Check HTTPRoutes are accepted
kubectl describe httproute <name> -n <namespace>

# Check certificate is ready
kubectl get certificates -n tailscale

# Check Envoy logs for incoming requests
kubectl logs -n envoy-gateway -l gateway.envoyproxy.io/owning-gateway-name=tailscale-gateway -c envoy --tail=20
```
