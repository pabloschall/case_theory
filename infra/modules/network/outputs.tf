output "network_id" {
  value = google_compute_network.main.id
}

output "network_name" {
  value = google_compute_network.main.name
}

output "subnetwork_id" {
  value = google_compute_subnetwork.main.id
}

output "subnetwork_name" {
  value = google_compute_subnetwork.main.name
}

output "private_service_connection" {
  value = google_service_networking_connection.private_services.id
}
