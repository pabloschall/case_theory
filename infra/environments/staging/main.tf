locals {
  name_prefix = "case-theory-stg"

  labels = {
    application = "case-theory"
    environment = "staging"
    managed_by  = "terraform"
  }

  required_services = [
    "artifactregistry.googleapis.com",
    "billingbudgets.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "compute.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "redis.googleapis.com",
    "run.googleapis.com",
    "secretmanager.googleapis.com",
    "servicenetworking.googleapis.com",
    "sqladmin.googleapis.com",
    "storage.googleapis.com",
    "sts.googleapis.com",
  ]
}

module "project_services" {
  source = "../../modules/project_services"

  project_id = var.project_id
  services   = toset(local.required_services)
}

module "budget" {
  source = "../../modules/budget"

  billing_account    = var.billing_account
  project_number     = var.project_number
  display_name       = "Case Theory staging monthly budget"
  monthly_amount_usd = var.monthly_budget_usd

  depends_on = [module.project_services]
}

module "artifact_registry" {
  source = "../../modules/artifact_registry"

  project_id    = var.project_id
  region        = var.region
  repository_id = "case-theory"
  labels        = local.labels

  depends_on = [module.project_services]
}

module "network" {
  source = "../../modules/network"

  project_id  = var.project_id
  region      = var.region
  name_prefix = local.name_prefix
  subnet_cidr = "10.10.0.0/24"

  depends_on = [module.project_services]
}

module "evidence_storage" {
  source = "../../modules/storage"

  project_id   = var.project_id
  region       = var.region
  bucket_name  = "${var.project_id}-staging-evidence"
  cors_origins = var.frontend_origin == "" ? [] : [var.frontend_origin]
  labels       = local.labels

  depends_on = [module.project_services]
}

module "identities" {
  source = "../../modules/identities"

  project_id           = var.project_id
  name_prefix          = local.name_prefix
  evidence_bucket_name = module.evidence_storage.bucket_name

  depends_on = [module.project_services]
}

module "secrets" {
  source = "../../modules/secrets"

  project_id = var.project_id
  labels     = local.labels
  secret_accessors = {
    "secret-key"      = [module.identities.service_account_emails.api, module.identities.service_account_emails.worker]
    "database-url"    = [module.identities.service_account_emails.api, module.identities.service_account_emails.worker, module.identities.service_account_emails.migration]
    "openai-api-key"  = [module.identities.service_account_emails.api, module.identities.service_account_emails.worker]
    "mailgun-api-key" = [module.identities.service_account_emails.worker]
    "fbi-api-key"     = [module.identities.service_account_emails.api, module.identities.service_account_emails.worker]
  }

  depends_on = [module.project_services]
}

module "cloud_sql" {
  count  = var.enable_cloud_sql ? 1 : 0
  source = "../../modules/cloud_sql"

  project_id          = var.project_id
  region              = var.region
  instance_name       = "${local.name_prefix}-postgres"
  database_name       = "case_theory"
  network_id          = module.network.network_id
  tier                = var.cloud_sql_tier
  deletion_protection = true
  labels              = local.labels

  depends_on = [module.network, module.project_services]
}

module "redis" {
  count  = var.enable_redis ? 1 : 0
  source = "../../modules/redis"

  project_id     = var.project_id
  region         = var.region
  instance_name  = "${local.name_prefix}-redis"
  network_id     = module.network.network_id
  memory_size_gb = var.redis_memory_size_gb
  labels         = local.labels

  depends_on = [module.network, module.project_services]
}

module "github_actions_identity" {
  source = "../../modules/github_actions_identity"

  project_id                     = var.project_id
  project_number                 = var.project_number
  billing_account                = var.billing_account
  state_bucket_name              = "${var.project_id}-tf-state"
  github_repository              = var.github_repository
  github_repository_id           = var.github_repository_id
  name_prefix                    = local.name_prefix
  runtime_service_account_emails = toset(values(module.identities.service_account_emails))

  depends_on = [module.project_services]
}
