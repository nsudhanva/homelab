output "worker_public_ip" {
  value       = data.oci_core_vnic.worker.public_ip_address
  description = "Public IP for the OCI worker"
}

output "worker_private_ip" {
  value       = data.oci_core_vnic.worker.private_ip_address
  description = "Private IP for the OCI worker"
}

output "worker_instance_id" {
  value       = oci_core_instance.worker.id
  description = "Instance OCID"
}
