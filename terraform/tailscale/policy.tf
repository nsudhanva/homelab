resource "tailscale_acl" "this" {
  acl = file("${path.module}/policy.hujson")

  lifecycle {
    prevent_destroy = true
  }
}
