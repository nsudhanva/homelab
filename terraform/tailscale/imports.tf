# These blocks adopted the settings that existed before Terraform managed the
# tailnet. After the first apply they are no-ops.
import {
  to = tailscale_acl.this
  id = "acl"
}

import {
  to = tailscale_dns_configuration.this
  id = "dns_configuration"
}

import {
  to = tailscale_tailnet_settings.this
  id = "tailnet_settings"
}
