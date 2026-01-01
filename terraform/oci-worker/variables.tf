variable "tenancy_ocid" {
  type        = string
  description = "OCI tenancy OCID"
}

variable "user_ocid" {
  type        = string
  description = "OCI user OCID"
}

variable "fingerprint" {
  type        = string
  description = "API key fingerprint"
}

variable "private_key_path" {
  type        = string
  description = "Path to the OCI API private key"
}

variable "region" {
  type        = string
  description = "OCI region"
}

variable "compartment_ocid" {
  type        = string
  description = "OCI compartment OCID"
}

variable "availability_domain" {
  type        = string
  description = "Availability domain for the worker"
}

variable "ssh_authorized_keys" {
  type        = string
  description = "SSH public key(s) for the instance"
}

variable "shape" {
  type        = string
  description = "Instance shape"
  default     = "VM.Standard.A1.Flex"
}

variable "shape_ocpus" {
  type        = number
  description = "OCPUs for the flex shape"
  default     = 2
}

variable "shape_memory_gbs" {
  type        = number
  description = "Memory in GB for the flex shape"
  default     = 12
}

variable "tailscale_auth_key" {
  type        = string
  description = "Tailscale auth key (from Vault)"
  sensitive   = true
}

variable "tailscale_hostname" {
  type        = string
  description = "Hostname for Tailscale"
  default     = "oci-worker"
}

variable "tailscale_advertise_tags" {
  type        = string
  description = "Comma-separated Tailscale tags"
  default     = "tag:k8s"
}

variable "tailscale_accept_routes" {
  type        = bool
  description = "Whether to accept routes"
  default     = true
}
