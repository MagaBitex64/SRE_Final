variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

variable "region" {
  type    = string
  default = "fra1"
}

variable "droplet_size" {
  type    = string
  default = "s-2vcpu-4gb"
}