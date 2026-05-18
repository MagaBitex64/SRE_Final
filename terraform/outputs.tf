output "app_server_ip" {
  description = "Public IP of App Server"
  value       = digitalocean_droplet.app_server.ipv4_address
}