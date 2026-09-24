locals {
  pool_name = "projects/${var.project_number}/locations/global/workloadIdentityPools/${google_iam_workload_identity_pool.github.workload_identity_pool_id}"

  accounts = {
    plan = {
      account_id   = "${var.name_prefix}-tf-plan"
      display_name = "Case Theory GitHub Terraform plan"
    }
    apply = {
      account_id   = "${var.name_prefix}-tf-apply"
      display_name = "Case Theory GitHub Terraform apply"
    }
    deploy = {
      account_id   = "${var.name_prefix}-deploy"
      display_name = "Case Theory GitHub application deploy"
    }
  }

  apply_project_roles = toset([
    "roles/artifactregistry.admin",
    "roles/cloudsql.admin",
    "roles/compute.networkAdmin",
    "roles/iam.serviceAccountAdmin",
    "roles/iam.serviceAccountUser",
    "roles/iam.workloadIdentityPoolAdmin",
    "roles/redis.admin",
    "roles/resourcemanager.projectIamAdmin",
    "roles/run.admin",
    "roles/secretmanager.admin",
    "roles/servicenetworking.networksAdmin",
    "roles/serviceusage.serviceUsageAdmin",
    "roles/storage.admin",
    "roles/viewer",
  ])

  deploy_project_roles = toset([
    "roles/artifactregistry.writer",
    "roles/run.admin",
  ])
}

resource "google_iam_workload_identity_pool" "github" {
  project                   = var.project_id
  workload_identity_pool_id = "github-actions"
  display_name              = "GitHub Actions"
  description               = "Keyless identities for ${var.github_repository} workflows"
}

resource "google_iam_workload_identity_pool_provider" "github" {
  project                            = var.project_id
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "case-theory"
  display_name                       = "Case Theory GitHub repository"

  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.actor"            = "assertion.actor"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_id"    = "assertion.repository_id"
    "attribute.repository_owner" = "assertion.repository_owner"
  }

  attribute_condition = var.github_repository_id != "" ? (
    "assertion.repository_id == '${var.github_repository_id}'"
  ) : "assertion.repository == '${var.github_repository}'"

  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "github" {
  for_each = local.accounts

  project      = var.project_id
  account_id   = each.value.account_id
  display_name = each.value.display_name
}

resource "google_service_account_iam_member" "plan_federation" {
  service_account_id = google_service_account.github["plan"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${local.pool_name}/attribute.repository/${var.github_repository}"
}

resource "google_service_account_iam_member" "apply_federation" {
  service_account_id = google_service_account.github["apply"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${local.pool_name}/subject/repo:${var.github_repository}:environment:staging-infrastructure"
}

resource "google_service_account_iam_member" "deploy_federation" {
  service_account_id = google_service_account.github["deploy"].name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principal://iam.googleapis.com/${local.pool_name}/subject/repo:${var.github_repository}:environment:staging"
}

resource "google_project_iam_member" "plan_viewer" {
  for_each = toset([
    "roles/iam.securityReviewer",
    "roles/viewer",
  ])

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.github["plan"].email}"
}

resource "google_storage_bucket_iam_member" "plan_state_reader" {
  bucket = var.state_bucket_name
  role   = "roles/storage.objectViewer"
  member = "serviceAccount:${google_service_account.github["plan"].email}"
}

resource "google_billing_account_iam_member" "plan_billing_viewer" {
  billing_account_id = var.billing_account
  role               = "roles/billing.viewer"
  member             = "serviceAccount:${google_service_account.github["plan"].email}"
}

resource "google_project_iam_member" "apply" {
  for_each = local.apply_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.github["apply"].email}"
}

resource "google_storage_bucket_iam_member" "apply_state_writer" {
  bucket = var.state_bucket_name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.github["apply"].email}"
}

resource "google_billing_account_iam_member" "apply_budget_manager" {
  billing_account_id = var.billing_account
  role               = "roles/billing.costsManager"
  member             = "serviceAccount:${google_service_account.github["apply"].email}"
}

resource "google_project_iam_member" "deploy" {
  for_each = local.deploy_project_roles

  project = var.project_id
  role    = each.value
  member  = "serviceAccount:${google_service_account.github["deploy"].email}"
}

resource "google_service_account_iam_member" "deploy_runtime_user" {
  for_each = var.runtime_service_account_emails

  service_account_id = "projects/${var.project_id}/serviceAccounts/${each.value}"
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${google_service_account.github["deploy"].email}"
}
