---
title: Manage Tailscale with Terraform
description: Change the tailnet policy, DNS, settings, and device tags through Terraform in terraform/tailscale, with plans in CI and a manual apply.
keywords:
  - tailscale terraform
  - tailscale policy file gitops
  - tailscale acl as code
  - terraform r2 backend
sidebar:
  order: 9
---

# Manage Tailscale with Terraform

Terraform in `terraform/tailscale/` manages the tailnet. Make every change to the policy file, DNS, tailnet settings, and device tags there. Do not change them in the Tailscale admin console. The console shows a banner that the policy is managed externally, and the weekly drift check fails when the tailnet and the code differ.

For the list of managed resources, credentials, and state, refer to [Tailscale Terraform Reference](/reference/tailscale-terraform/).

## Step 1: Set up the credentials (one time)

Terraform needs two credentials. Create them, store them in Vault, and copy them to GitHub.

Create a Tailscale OAuth client for Terraform in the admin console under **Settings > Trust credentials**:

- Description: `terraform`
- Scopes: `policy_file`, `devices:posture_attributes`, `dns`, `devices:core`, and `feature_settings`
- Tags for `devices:core`: `tag:server` (Terraform can apply only these tags to devices)

Create a Cloudflare R2 API token with **Object Read & Write** on the `homelab-terraform-state` bucket only. Note the access key ID, the secret access key, and the S3 endpoint (`https://<account-id>.r2.cloudflarestorage.com`).

Store both in Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/terraform \
  client_id="REPLACE_ME" client_secret="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/terraform/state \
  access_key_id="REPLACE_ME" secret_access_key="REPLACE_ME" endpoint="REPLACE_ME"
```

Copy them into the GitHub Actions secrets. The script reads Vault and pipes each value to `gh secret set`, so the values do not show in your terminal:

```bash
export VAULT_TOKEN="REPLACE_ME"
scripts/tailscale-terraform.sh github-secrets
```

## Step 2: Change the tailnet

Edit the files in `terraform/tailscale/`:

| To change | Edit |
| --- | --- |
| Access rules, SSH rules, tag owners, tests | `policy.hujson` |
| Nameservers, split DNS, MagicDNS | `dns.tf` |
| Tailnet settings (key expiry, approvals, HTTPS) | `settings.tf` |
| Tags on a device | `devices.tf` |

Open a pull request. The `Tailscale` workflow runs `terraform fmt`, `validate`, and `plan`. Read the plan in the job log.

Merge the pull request. The workflow plans again on `master`.

Then apply. In GitHub, open **Actions > Tailscale > Run workflow**, select `master`, check **Apply the plan to the tailnet**, and run it. The job plans and then applies that exact plan.

Tailscale validates every policy change, including the `sshTests` in `policy.hujson`. If a test fails, the apply fails and the old policy stays.

## Step 3: Run Terraform locally (optional)

The wrapper script reads the credentials from Vault and runs Terraform in `terraform/tailscale/`:

```bash
export VAULT_TOKEN="REPLACE_ME"
scripts/tailscale-terraform.sh init
scripts/tailscale-terraform.sh plan
```

Apply from CI when you can, so that every change has a log. To apply locally, run `scripts/tailscale-terraform.sh apply`. The S3 backend uses a lock file in R2, so a local run and a CI run cannot apply at the same time.

## Common changes

### Tag a device

Add a data source and a `tailscale_device_tags` resource to `devices.tf`. Add the tag to `tagOwners` in `policy.hujson` first, and add the tag to the Terraform OAuth client, or the apply fails:

```hcl
data "tailscale_device" "workstation" {
  hostname = "workstation"
}

resource "tailscale_device_tags" "workstation" {
  device_id = data.tailscale_device.workstation.node_id
  tags      = ["tag:server"]
}
```

Do not manage devices that the Tailscale Kubernetes operator creates (`tag:k8s`). The operator owns their tags.

### Add a fallback nameserver

Tailnet DNS uses only Technitium in the cluster. If the cluster is down, tailnet clients cannot resolve names. To add a fallback, add more `nameservers` blocks to `dns.tf`.

Tailscale queries all global nameservers in parallel and uses the fastest answer, not only when Technitium fails. So a fallback must block ads the way Technitium does, for example AdGuard DNS (`94.140.14.14`, `94.140.15.15`). If you add a resolver that does not block ads, such as `1.1.1.1`, ads come through whenever that resolver answers first.

To test a candidate, compare a normal domain and an ad domain:

```bash
dig +short example.com @94.140.14.14
dig +short doubleclick.net @94.140.14.14
```

A blocking resolver returns an address for `example.com` and `0.0.0.0` (or no answer) for `doubleclick.net`.

### Fix drift

The scheduled run fails when someone changes the tailnet in the console. Read the plan in the failed job. To keep the console change, copy it into the Terraform files. To undo it, run the apply.

## Rotate credentials

Create the new credential (OAuth client or R2 token) as in Step 1. Write it to Vault with `vault kv put`, and run `scripts/tailscale-terraform.sh github-secrets`. Run the `Tailscale` workflow without apply, and make sure the plan succeeds. Then delete the old credential.

## Break glass

If CI and Vault are down and you must change the tailnet now, edit it in the admin console. Then copy the change into `terraform/tailscale/` in a pull request, so the next plan is empty.
