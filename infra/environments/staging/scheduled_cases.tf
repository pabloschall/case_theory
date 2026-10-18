locals {
  scheduled_case_lanes = var.enable_scheduled_cases ? {
    recent = {
      schedule = "0 1 * * 1"
      cadence  = "weekly"
    }
    historical = {
      schedule = "0 2 * * 1"
      cadence  = "weekly"
    }
    paranormal = {
      schedule = "0 3 * * 1"
      cadence  = "weekly"
    }
  } : {}

  scheduled_case_env = {
    ENVIRONMENT                 = "staging"
    FRONTEND_URL                = var.frontend_origin
    COOKIE_SECURE               = "true"
    STORAGE_PROVIDER            = "gcs"
    GCS_PROJECT_ID              = var.project_id
    GCS_BUCKET                  = module.evidence_storage.bucket_name
    GCS_SIGNING_SERVICE_ACCOUNT = module.identities.service_account_emails.worker
  }

  scheduled_case_secrets = {
    DATABASE_URL       = "database-url"
    SECRET_KEY         = "secret-key"
    OPENAI_API_KEY     = "openai-api-key"
    MAILGUN_API_KEY    = "mailgun-api-key"
    MAILGUN_BASE_URL   = "mailgun-base-url"
    MAILGUN_FROM_EMAIL = "mailgun-from-email"
  }
}

resource "google_service_account" "scheduled_case_invoker" {
  count = var.enable_scheduled_cases ? 1 : 0

  project      = var.project_id
  account_id   = "${local.name_prefix}-scheduler"
  display_name = "Case Theory scheduled case invoker"
}

resource "google_cloud_run_v2_job" "scheduled_case" {
  for_each = local.scheduled_case_lanes

  project             = var.project_id
  name                = "${local.name_prefix}-${each.key}-draft"
  location            = var.region
  deletion_protection = false
  labels              = local.labels

  template {
    task_count  = 1
    parallelism = 1

    template {
      service_account = module.identities.service_account_emails.worker
      timeout         = "3600s"
      max_retries     = 0

      containers {
        image   = var.scheduled_cases_backend_image
        command = ["python", "-m", "app.scheduled_cases"]
        args    = [each.key]

        resources {
          limits = {
            cpu    = "1"
            memory = "2Gi"
          }
        }

        dynamic "env" {
          for_each = local.scheduled_case_env
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.scheduled_case_secrets
          content {
            name = env.key
            value_source {
              secret_key_ref {
                secret  = module.secrets.secret_ids[env.value]
                version = "latest"
              }
            }
          }
        }
      }

      vpc_access {
        egress = "PRIVATE_RANGES_ONLY"
        network_interfaces {
          network    = module.network.network_name
          subnetwork = module.network.subnetwork_name
        }
      }
    }
  }

  lifecycle {
    # The staging release workflow advances the jobs to each new backend image.
    ignore_changes = [template[0].template[0].containers[0].image]

    precondition {
      condition     = var.enable_cloud_sql && var.frontend_origin != "" && var.scheduled_cases_backend_image != ""
      error_message = "Scheduled cases require Cloud SQL, frontend_origin, and an immutable backend image."
    }
  }

  depends_on = [module.project_services, module.secrets]
}

resource "google_cloud_run_v2_job_iam_member" "scheduled_case_invoker" {
  for_each = local.scheduled_case_lanes

  project  = var.project_id
  location = google_cloud_run_v2_job.scheduled_case[each.key].location
  name     = google_cloud_run_v2_job.scheduled_case[each.key].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduled_case_invoker[0].email}"
}

resource "google_cloud_scheduler_job" "scheduled_case" {
  for_each = local.scheduled_case_lanes

  project          = var.project_id
  region           = var.region
  name             = "${local.name_prefix}-${each.key}-draft"
  description      = "Generate one public ${each.key} case ${each.value.cadence}"
  schedule         = each.value.schedule
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.scheduled_case[each.key].name}:run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.scheduled_case_invoker[0].email
    }
  }

  depends_on = [
    module.github_actions_identity,
    module.project_services,
    google_cloud_run_v2_job_iam_member.scheduled_case_invoker,
  ]
}
