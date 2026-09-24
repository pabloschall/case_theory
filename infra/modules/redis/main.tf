resource "google_redis_instance" "cache" {
  project        = var.project_id
  name           = var.instance_name
  display_name   = "Case Theory staging Redis"
  region         = var.region
  tier           = "BASIC"
  memory_size_gb = var.memory_size_gb
  redis_version  = "REDIS_7_2"

  authorized_network = var.network_id
  connect_mode       = "PRIVATE_SERVICE_ACCESS"
  labels             = var.labels

}
