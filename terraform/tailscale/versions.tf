terraform {
  required_version = ">= 1.16.0, < 2.0.0"

  required_providers {
    tailscale = {
      source  = "tailscale/tailscale"
      version = "~> 0.29.3"
    }
  }

  # The R2 endpoint contains the Cloudflare account ID, so it is passed at init
  # time with -backend-config instead of being committed.
  backend "s3" {
    bucket                      = "homelab-terraform-state"
    key                         = "tailscale/terraform.tfstate"
    region                      = "auto"
    use_path_style              = true
    use_lockfile                = true
    skip_credentials_validation = true
    skip_metadata_api_check     = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
    skip_s3_checksum            = true
  }
}
