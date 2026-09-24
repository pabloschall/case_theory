output "service_account_emails" {
  value = {
    for name, account in google_service_account.runtime : name => account.email
  }
}
