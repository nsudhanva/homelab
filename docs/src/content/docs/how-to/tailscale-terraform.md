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

Terraform in `terraform/tailscale/` manages the tailnet. Make every change to the policy file, DNS, tailnet settings, and device tags there. Do not change them in the Tailscale admin console. The console shows a banner that an external system manages the policy. The weekly drift check fails when the tailnet and the code are different.

For the list of managed resources, credentials, and state, refer to [Tailscale Terraform Reference](/reference/tailscale-terraform/).

## Step 1: Set up the credentials (one time)

Terraform needs two credentials. Create them, store them in Vault, and copy them to GitHub.

Create a Tailscale OAuth client for Terraform in the admin console under **Settings > Trust credentials**:

- Description: `terraform`
- Scopes: `policy_file`, `devices:posture_attributes`, `dns`, `devices:core`, and `feature_settings`
- Tags for `devices:core`: `tag:server` (Terraform can apply only these tags to devices)

Create a Cloudflare R2 API token with **Object Read & Write** on the `homelab-terraform-state` bucket only. Record the access key ID, the secret access key, and the S3 endpoint (`https://<account-id>.r2.cloudflarestorage.com`).

Store both credentials in Vault:

```bash
kubectl -n vault exec -it vault-0 -- vault kv put kv/tailscale/terraform \
  client_id="REPLACE_ME" client_secret="REPLACE_ME"

kubectl -n vault exec -it vault-0 -- vault kv put kv/terraform/state \
  access_key_id="REPLACE_ME" secret_access_key="REPLACE_ME" endpoint="REPLACE_ME"
```

Copy the credentials into the GitHub Actions secrets. The script reads Vault and sends each value to `gh secret set`, so the values do not show in your terminal.

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

Merge the pull request. The workflow makes a new plan on `master`.

Apply the plan. In GitHub, open **Actions > Tailscale > Run workflow**. Select `master`, check **Apply the plan to the tailnet**, and run the workflow. The job makes a plan and then applies that plan.

Tailscale validates every policy change, including the `sshTests` in `policy.hujson`. If a test fails, the apply fails and the tailnet keeps the current policy.

## Step 3: Run Terraform locally (optional)

The wrapper script reads the credentials from Vault and runs Terraform in `terraform/tailscale/`:

```bash
export VAULT_TOKEN="REPLACE_ME"
scripts/tailscale-terraform.sh init
scripts/tailscale-terraform.sh plan
```

Apply from CI, so that every change has a job log. To apply locally, run `scripts/tailscale-terraform.sh apply`. The S3 backend uses a lock file in R2, so a local run and a CI run cannot apply at the same time.

## Common changes

### Tag a device

Add a data source and a `tailscale_device_tags` resource to `devices.tf`. Before you apply, add the tag to `tagOwners` in `policy.hujson` and to the Terraform OAuth client. If the tag is not in both, the apply fails.

```hcl
data "tailscale_device" "workstation" {
  hostname = "workstation"
}

resource "tailscale_device_tags" "workstation" {
  device_id = data.tailscale_device.workstation.node_id
  tags      = ["tag:server"]
}
```

Do not manage the devices that the Tailscale Kubernetes operator creates (`tag:k8s`). The operator owns their tags.

### Add a fallback nameserver

Tailnet DNS has one global nameserver, Technitium in the cluster. When the cluster is down, tailnet clients cannot resolve names. To add a fallback, add a `nameservers` block to `dns.tf`.

Use only a fallback nameserver that blocks ads. Tailscale queries all global nameservers at the same time and uses the first answer, so each global nameserver must block ads. AdGuard DNS (`94.140.14.14`, `94.140.15.15`) is a resolver that blocks ads.

To test a resolver, compare a normal domain and an ad domain:

```bash
dig +short example.com @94.140.14.14
dig +short doubleclick.net @94.140.14.14
```

A resolver that blocks ads returns an address for `example.com`. For `doubleclick.net`, it returns `0.0.0.0` or no answer.

### Fix drift

The scheduled run fails when a person changes the tailnet in the console. Read the plan in the failed job. To keep the console change, copy it into the Terraform files. To remove the console change, run the apply.

## Rotate credentials

Step 1: Create the new credential (OAuth client or R2 token) as in Step 1 above.

Step 2: Write the new credential to Vault with `vault kv put`.

Step 3: Run `scripts/tailscale-terraform.sh github-secrets`.

Step 4: Run the `Tailscale` workflow without apply. Make sure that the plan succeeds.

Step 5: Delete the old credential.

## Break glass

If CI and Vault are down and you must change the tailnet immediately, edit it in the admin console. Then copy the change into `terraform/tailscale/` in a pull request, so that the next plan is empty.
