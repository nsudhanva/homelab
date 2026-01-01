data "oci_identity_availability_domain" "ad" {
  compartment_id = var.compartment_ocid
  ad_number      = tonumber(regex("AD-(\\d+)$", var.availability_domain)[0])
}

data "oci_core_images" "ubuntu" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "24.04"
  shape                    = var.shape
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

resource "oci_core_vcn" "worker" {
  compartment_id = var.compartment_ocid
  display_name   = "oci-worker-vcn"
  cidr_block     = "10.42.0.0/16"
  dns_label      = "ociworker"
}

resource "oci_core_internet_gateway" "worker" {
  compartment_id = var.compartment_ocid
  display_name   = "oci-worker-igw"
  vcn_id         = oci_core_vcn.worker.id
  enabled        = true
}

resource "oci_core_nat_gateway" "worker" {
  compartment_id = var.compartment_ocid
  display_name   = "oci-worker-nat"
  vcn_id         = oci_core_vcn.worker.id
}

resource "oci_core_route_table" "worker" {
  compartment_id = var.compartment_ocid
  display_name   = "oci-worker-rt"
  vcn_id         = oci_core_vcn.worker.id

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.worker.id
  }
}

resource "oci_core_security_list" "worker" {
  compartment_id = var.compartment_ocid
  display_name   = "oci-worker-sl"
  vcn_id         = oci_core_vcn.worker.id

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 41641
      max = 41641
    }
  }

  egress_security_rules {
    protocol    = "all"
    destination = "0.0.0.0/0"
  }
}

resource "oci_core_subnet" "worker" {
  compartment_id      = var.compartment_ocid
  display_name        = "oci-worker-subnet"
  vcn_id              = oci_core_vcn.worker.id
  cidr_block          = "10.42.10.0/24"
  route_table_id      = oci_core_route_table.worker.id
  security_list_ids   = [oci_core_security_list.worker.id]
  dhcp_options_id     = oci_core_vcn.worker.default_dhcp_options_id
  prohibit_public_ip_on_vnic = false
  dns_label           = "worker"
}

resource "oci_core_instance" "worker" {
  compartment_id      = var.compartment_ocid
  availability_domain = data.oci_identity_availability_domain.ad.name
  display_name        = "oci-worker"
  shape               = var.shape

  shape_config {
    ocpus         = var.shape_ocpus
    memory_in_gbs = var.shape_memory_gbs
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.worker.id
    assign_public_ip = true
    display_name     = "oci-worker-vnic"
    hostname_label   = "oci-worker"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_authorized_keys
    user_data           = base64encode(templatefile("${path.module}/cloud-init.sh.tmpl", {
      tailscale_auth_key       = var.tailscale_auth_key
      tailscale_hostname       = var.tailscale_hostname
      tailscale_advertise_tags = var.tailscale_advertise_tags
      tailscale_accept_routes  = var.tailscale_accept_routes
    }))
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu.images[0].id
  }
}

data "oci_core_vnic_attachments" "worker" {
  compartment_id = var.compartment_ocid
  instance_id    = oci_core_instance.worker.id
}

data "oci_core_vnic" "worker" {
  vnic_id = data.oci_core_vnic_attachments.worker.vnic_attachments[0].vnic_id
}
