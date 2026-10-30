# Devices that the Tailscale Kubernetes operator creates. Terraform only reads
# them; the operator owns their tags and keys.
data "tailscale_device" "technitium_dns" {
  hostname = "technitium-dns"
}

data "tailscale_device" "split_dns_resolver" {
  hostname = "tailscale-dns"
}

data "tailscale_device" "legion" {
  hostname = "legion"
}

locals {
  technitium_dns_ipv4     = one([for address in data.tailscale_device.technitium_dns.addresses : address if !strcontains(address, ":")])
  split_dns_resolver_ipv4 = one([for address in data.tailscale_device.split_dns_resolver.addresses : address if !strcontains(address, ":")])
}

# legion is the K3s server. tag:server lets the Ansible Provision workflow
# (tag:ci) reach it over Tailscale SSH.
resource "tailscale_device_tags" "legion" {
  device_id = data.tailscale_device.legion.node_id
  tags      = ["tag:server"]
}
