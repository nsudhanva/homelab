# Technitium in the cluster is the global tailnet resolver. sudhanva.me goes to
# the split-DNS CoreDNS resolver, which answers HTTPRoute hostnames with the
# Tailscale Gateway IP.
resource "tailscale_dns_configuration" "this" {
  magic_dns          = true
  override_local_dns = true
  search_paths       = []

  nameservers {
    address = local.technitium_dns_ipv4
  }

  split_dns {
    domain = "sudhanva.me"

    nameservers {
      address = local.split_dns_resolver_ipv4
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
