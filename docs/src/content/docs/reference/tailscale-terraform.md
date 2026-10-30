---
title: Tailscale Terraform Reference
description: Files, managed resources, credentials, state, and CI for the Terraform configuration that manages the tailnet.
keywords:
  - tailscale terraform reference
  - tailscale provider
  - terraform state r2
sidebar:
  order: 45
---

# Tailscale Terraform Reference

`terraform/tailscale/` manages the tailnet with the [Tailscale Terraform provider](https://registry.terraform.io/providers/tailscale/tailscale/latest/docs). To make changes, refer to [Manage Tailscale with Terraform](/how-to/tailscale-terraform/).

## Files

| File | Contents |
| --- | --- |
| `versions.tf` | Terraform and provider versions, and the R2 state backend |
| `providers.tf` | The `tailscale` provider. Credentials come from environment variables |
| `policy.hujson` | The tailnet policy file: tag owners, access rules, SSH rules, node attributes, and `sshTests` |
| `policy.tf` | `tailscale_acl` that applies `policy.hujson` |
| `dns.tf` | `tailscale_dns_configuration`: nameservers, split DNS, MagicDNS |
| `settings.tf` | `tailscale_tailnet_settings` |
| `devices.tf` | Device lookups and `tailscale_device_tags` |
| `imports.tf` | `import` blocks that adopted the settings that existed before Terraform |
| `.terraform.lock.hcl` | Provider checksums for macOS and Linux. Commit it |

## Managed resources

| Resource | What it controls |
| --- | --- |
| `tailscale_acl.this` | The whole policy file |
| `tailscale_dns_configuration.this` | Global nameservers (Technitium `technitium-dns`, with AdGuard DNS `94.140.14.14` and `94.140.15.15` as the fallback), split DNS for `sudhanva.me` (`tailscale-dns`), MagicDNS, override local DNS |
| `tailscale_tailnet_settings.this` | Key expiry (180 days), device and user approval, auto updates, HTTPS, flow logging, external policy management |
| `tailscale_device_tags.legion` | `tag:server` on `legion` |

`dns.tf` looks up the Tailscale IPs of `technitium-dns` and `tailscale-dns` by hostname, so the IPs are not hardcoded. If the operator recreates one of these proxies, the next plan updates DNS.

These three resources have `prevent_destroy`. Terraform refuses a plan that deletes the policy, DNS, or settings.

## Not managed

| Item | Reason | Where it is managed |
| --- | --- | --- |
| OAuth clients and auth keys | Terraform would store their secrets in state | Admin console, then Vault |
| Devices with `tag:k8s` | The Tailscale Kubernetes operator owns them | `infrastructure/tailscale/` |
| User devices | Each user owns them | Tailscale clients |
| Device options such as Tailscale SSH and `--accept-dns` | They are set on the device, not through the API | `ansible/roles/tailscale/` or `tailscale set` on the device |
| Contacts | They hold personal email addresses, and this repository is public | Admin console |
| Log streaming | The plan does not include it | Not used |

## Tags

| Tag | Owner | Used by |
| --- | --- | --- |
| `tag:k8s-operator` | Admins | Owner of `tag:k8s` |
| `tag:k8s` | `tag:k8s-operator` | Operator and its proxies (Gateway, DNS) |
| `tag:ci` | Admins | GitHub Actions runners of the `Ansible Provision` workflow |
| `tag:server` | Admins | `legion`. `tag:ci` can SSH to it as `sudhanva` |

## Credentials

| Credential | Vault path | Properties | GitHub Actions secret |
| --- | --- | --- | --- |
| Tailscale OAuth client for Terraform | `kv/tailscale/terraform` | `client_id`, `client_secret` | `TAILSCALE_TF_OAUTH_CLIENT_ID`, `TAILSCALE_TF_OAUTH_CLIENT_SECRET` |
| R2 token for the state bucket | `kv/terraform/state` | `access_key_id`, `secret_access_key`, `endpoint` | `TF_STATE_R2_ACCESS_KEY_ID`, `TF_STATE_R2_SECRET_ACCESS_KEY`, `TF_STATE_R2_ENDPOINT` |

`scripts/tailscale-terraform.sh github-secrets` copies the Vault values into the GitHub secrets. The Terraform OAuth client needs the scopes `policy_file`, `devices:posture_attributes`, `dns`, `devices:core`, and `feature_settings`, and the tag `tag:server`.

## State

| Setting | Value |
| --- | --- |
| Backend | `s3` on Cloudflare R2 |
| Bucket | `homelab-terraform-state` (private) |
| Key | `tailscale/terraform.tfstate` |
| Locking | `use_lockfile = true` (a lock object in R2) |
| Endpoint | Passed with `-backend-config` from `kv/terraform/state` or the `TF_STATE_R2_ENDPOINT` secret. It contains the Cloudflare account ID, so it is not in the repository |

Never commit state, plan files, or `.tfvars` files. `.gitignore` excludes them.

## CI

The `Tailscale` workflow (`.github/workflows/tailscale.yaml`) runs `terraform fmt -check`, `init`, `validate`, and `plan`:

| Trigger | Result |
| --- | --- |
| Pull request that changes `terraform/tailscale/**` | Plan. Pull requests from forks are skipped because they cannot read secrets |
| Push to `master` | Plan |
| Monday 14:17 UTC | Plan. The job fails when the tailnet differs from the code (drift) |
| Manual run with **Apply the plan to the tailnet** | Plan, then apply that plan |

The workflow does not upload plan files, and it never applies without the manual input.

## Versions

| Tool | Version |
| --- | --- |
| Terraform (CI) | `1.17.1` |
| Terraform (required) | `>= 1.16.0, < 2.0.0` |
| `tailscale/tailscale` provider | `~> 0.29.3`, locked in `.terraform.lock.hcl` |
| `hashicorp/setup-terraform` | `v4` |
