# Technitium in the cluster is the global tailnet resolver. sudhanva.me goes to
# the split-DNS CoreDNS resolver, which answers HTTPRoute hostnames with the
# Tailscale Gateway IP.
#
# AdGuard DNS is the fallback for when the cluster is down. Tailscale queries
# all global nameservers in parallel and uses the fastest answer, so the
# fallback must block ads like Technitium does. A plain resolver such as
# 1.1.1.1 would let ads through whenever it answers first.
resource "tailscale_dns_configuration" "this" {
  magic_dns          = true
  override_local_dns = true
  search_paths       = []

  nameservers {
    address = local.technitium_dns_ipv4
  }

  nameservers {
    address = "94.140.14.14"
  }

  nameservers {
    address = "94.140.15.15"
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
