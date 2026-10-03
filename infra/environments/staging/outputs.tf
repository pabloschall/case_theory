output "artifact_repository" {
  value = module.artifact_registry.docker_repository
}

output "budget_id" {
  value = module.budget.budget_id
}

output "evidence_bucket" {
  value = module.evidence_storage.bucket_name
}

output "runtime_service_accounts" {
  value = module.identities.service_account_emails
}

output "secret_ids" {
  value = module.secrets.secret_ids
}

output "network" {
  value = {
    name   = module.network.network_name
    subnet = module.network.subnetwork_name
  }
}

output "cloud_sql" {
  value = var.enable_cloud_sql ? {
    instance_name = module.cloud_sql[0].instance_name
    connection    = module.cloud_sql[0].connection_name
    private_ip    = module.cloud_sql[0].private_ip_address
    database      = module.cloud_sql[0].database_name
  } : null
}

output "redis" {
  value = var.enable_redis ? {
    host = module.redis[0].host
    port = module.redis[0].port
  } : null
}

output "github_actions" {
  value = {
    workload_identity_provider = module.github_actions_identity.workload_identity_provider
    service_accounts           = module.github_actions_identity.service_account_emails
  }
}

output "custom_domain_ipv4" {
  description = "Add HostGator A records for @ and www with this address after enabling custom_domain."
  value       = var.custom_domain == "" ? null : google_compute_global_address.frontend[0].address
}
