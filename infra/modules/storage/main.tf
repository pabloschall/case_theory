resource "google_storage_bucket" "evidence" {
  project                     = var.project_id
  name                        = var.bucket_name
  location                    = var.region
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = false
  labels                      = var.labels

  versioning {
    enabled = true
  }

  soft_delete_policy {
    retention_duration_seconds = 604800
  }

  dynamic "cors" {
    for_each = length(var.cors_origins) == 0 ? [] : [1]
    content {
      origin          = var.cors_origins
      method          = ["GET", "HEAD", "PUT"]
      response_header = ["Content-Type", "ETag"]
      max_age_seconds = 3600
    }
  }

  lifecycle {
    prevent_destroy = true
  }
}
