resource "tailscale_tailnet_settings" "this" {
  acls_externally_managed_on                  = true
  acls_external_link                          = "https://github.com/nsudhanva/homelab/blob/master/terraform/tailscale/policy.hujson"
  devices_approval_on                         = false
  devices_auto_updates_on                     = false
  devices_key_duration_days                   = 180
  https_enabled                               = true
  network_flow_logging_on                     = false
  posture_identity_collection_on              = false
  regional_routing_on                         = false
  users_approval_on                           = false
  users_role_allowed_to_join_external_tailnet = "admin"

  lifecycle {
    prevent_destroy = true
  }
}
