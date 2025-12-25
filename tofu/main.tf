resource "proxmox_lxc" "volvo_cracker_test" {
  target_node  = var.target_node
  hostname     = "volvo-cracker-test"
  ostemplate   = "pve-07-iso-nvme:vztmpl/debian-13-standard_13.1-2_amd64.tar.zst"
  password     = "Cracker123!" # Default password
  unprivileged = true
  ostype       = "debian"

  # CPU and Memory
  cores  = 2
  memory = 1024

  # Storage
  rootfs {
    storage = "pve-07-disk-nvme"
    size    = "8G"
  }

  # Network
  network {
    name   = "eth0"
    bridge = "vmbr0"
    ip     = "dhcp"
  }

  # Features
  features {
    nesting = true
  }

  ssh_public_keys = <<-EOT
    ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC2Ge3By2ttnCFLKu+JiUGv6th3T6JNU+kgR/XCOnfKd uzanto@la-devel-11
  EOT
}

output "container_ip" {
  value = proxmox_lxc.volvo_cracker_test.network[0].ip
}
