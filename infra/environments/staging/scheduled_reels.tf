locals {
  scheduled_reel_env = {
    ENVIRONMENT                  = "staging"
    FRONTEND_URL                 = var.frontend_origin
    COOKIE_SECURE                = "true"
    STORAGE_PROVIDER             = "gcs"
    GCS_PROJECT_ID               = var.project_id
    GCS_BUCKET                   = module.evidence_storage.bucket_name
    GCS_SIGNING_SERVICE_ACCOUNT  = module.identities.service_account_emails.worker
    REEL_SITE_LABEL              = "case-researcher.com"
    REEL_VISUAL_PROVIDER         = "vertex_veo"
    REEL_VIDEO_PROJECT_ID        = var.project_id
    REEL_VIDEO_LOCATION          = var.region
    REEL_VIDEO_MODEL             = "veo-3.1-fast-generate-001"
    REEL_VIDEO_DURATION_SECONDS  = "8"
    REEL_VIDEO_PERSON_GENERATION = "allow_adult"
    REEL_VIDEO_FALLBACK_TO_IMAGE = "true"
    YOUTUBE_PRIVACY_STATUS       = "public"
  }

  scheduled_reel_secrets = {
    DATABASE_URL          = "database-url"
    SECRET_KEY            = "secret-key"
    OPENAI_API_KEY        = "openai-api-key"
    MAILGUN_API_KEY       = "mailgun-api-key"
    MAILGUN_BASE_URL      = "mailgun-base-url"
    MAILGUN_FROM_EMAIL    = "mailgun-from-email"
    YOUTUBE_CLIENT_ID     = "youtube-client-id"
    YOUTUBE_CLIENT_SECRET = "youtube-client-secret"
    YOUTUBE_REFRESH_TOKEN = "youtube-refresh-token"
    YOUTUBE_CHANNEL_ID    = "youtube-channel-id"
  }
}

resource "google_service_account" "scheduled_reel_invoker" {
  count = var.enable_scheduled_reels ? 1 : 0

  project      = var.project_id
  account_id   = "${local.name_prefix}-reel-scheduler"
  display_name = "Case Theory scheduled reel invoker"
}

resource "google_project_iam_member" "scheduled_reel_vertex_user" {
  count = var.enable_scheduled_reels ? 1 : 0

  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${module.identities.service_account_emails.worker}"
}

resource "google_cloud_run_v2_job" "scheduled_reel" {
  count = var.enable_scheduled_reels ? 1 : 0

  project             = var.project_id
  name                = "${local.name_prefix}-youtube-short"
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
        command = ["python", "-m", "app.scheduled_reels"]

        resources {
          limits = {
            cpu    = "2"
            memory = "4Gi"
          }
        }

        dynamic "env" {
          for_each = local.scheduled_reel_env
          content {
            name  = env.key
            value = env.value
          }
        }

        dynamic "env" {
          for_each = local.scheduled_reel_secrets
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
    ignore_changes = [template[0].template[0].containers[0].image]

    precondition {
      condition     = var.enable_cloud_sql && var.frontend_origin != "" && var.scheduled_cases_backend_image != ""
      error_message = "Scheduled reels require Cloud SQL, frontend_origin, and an immutable backend image."
    }
  }

  depends_on = [module.project_services, module.secrets, google_project_iam_member.scheduled_reel_vertex_user]
}

resource "google_cloud_run_v2_job_iam_member" "scheduled_reel_invoker" {
  count = var.enable_scheduled_reels ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_job.scheduled_reel[0].location
  name     = google_cloud_run_v2_job.scheduled_reel[0].name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.scheduled_reel_invoker[0].email}"
}

resource "google_cloud_run_v2_job_iam_member" "scheduled_reel_api_invoker" {
  count = var.enable_scheduled_reels ? 1 : 0

  project  = var.project_id
  location = google_cloud_run_v2_job.scheduled_reel[0].location
  name     = google_cloud_run_v2_job.scheduled_reel[0].name
  role     = "roles/run.jobsExecutorWithOverrides"
  member   = "serviceAccount:${module.identities.service_account_emails.api}"
}

resource "google_cloud_scheduler_job" "scheduled_reel" {
  count = var.enable_scheduled_reels ? 1 : 0

  project          = var.project_id
  region           = var.region
  name             = "${local.name_prefix}-youtube-short"
  description      = "Generate and publish one sourced YouTube Short nightly"
  schedule         = "0 4 * * *"
  time_zone        = "Etc/UTC"
  attempt_deadline = "320s"

  retry_config {
    retry_count = 1
  }

  http_target {
    http_method = "POST"
    uri         = "https://run.googleapis.com/v2/projects/${var.project_id}/locations/${var.region}/jobs/${google_cloud_run_v2_job.scheduled_reel[0].name}:run"
    body        = base64encode("{}")

    headers = {
      "Content-Type" = "application/json"
    }

    oauth_token {
      service_account_email = google_service_account.scheduled_reel_invoker[0].email
    }
  }

  depends_on = [
    module.github_actions_identity,
    module.project_services,
    google_cloud_run_v2_job_iam_member.scheduled_reel_invoker,
  ]
}
