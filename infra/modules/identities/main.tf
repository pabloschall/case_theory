locals {
  accounts = {
    api = {
      account_id   = "${var.name_prefix}-api"
      display_name = "Case Theory staging API"
    }
    worker = {
      account_id   = "${var.name_prefix}-worker"
      display_name = "Case Theory staging worker"
    }
    migration = {
      account_id   = "${var.name_prefix}-migration"
      display_name = "Case Theory staging database migrations"
    }
  }

  project_roles = {
    api_cloudsql       = ["api", "roles/cloudsql.client"]
    worker_cloudsql    = ["worker", "roles/cloudsql.client"]
    migration_cloudsql = ["migration", "roles/cloudsql.client"]
  }

  bucket_roles = {
    api_objects    = ["api", "roles/storage.objectAdmin"]
    worker_objects = ["worker", "roles/storage.objectAdmin"]
  }
}

resource "google_service_account" "runtime" {
  for_each = local.accounts

  project      = var.project_id
  account_id   = each.value.account_id
  display_name = each.value.display_name
}

resource "google_project_iam_member" "project_role" {
  for_each = local.project_roles

  project = var.project_id
  role    = each.value[1]
  member  = "serviceAccount:${google_service_account.runtime[each.value[0]].email}"
}

resource "google_storage_bucket_iam_member" "bucket_role" {
  for_each = local.bucket_roles

  bucket = var.evidence_bucket_name
  role   = each.value[1]
  member = "serviceAccount:${google_service_account.runtime[each.value[0]].email}"
}

resource "google_service_account_iam_member" "api_signer" {
  service_account_id = google_service_account.runtime["api"].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.runtime["api"].email}"
}

resource "google_service_account_iam_member" "worker_signer" {
  service_account_id = google_service_account.runtime["worker"].name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.runtime["worker"].email}"
}
