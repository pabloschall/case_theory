output "workload_identity_provider" {
  description = "Full provider resource name for google-github-actions/auth."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "service_account_emails" {
  description = "GitHub Actions service accounts by responsibility."
  value       = { for key, account in google_service_account.github : key => account.email }
}
