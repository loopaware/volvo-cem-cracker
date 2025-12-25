variable "proxmox_token_id" {
  type      = string
  sensitive = false
}

variable "proxmox_token_secret" {
  type      = string
  sensitive = true
}

variable "target_node" {
  type    = string
  default = "la-vmh-07"
}
