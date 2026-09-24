output "state_bucket_name" {
  description = "Bucket to configure in environment GCS backends."
  value       = google_storage_bucket.terraform_state.name
}
