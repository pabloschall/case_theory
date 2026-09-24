variable "project_id" {
  description = "Google Cloud project ID."
  type        = string
}

variable "project_number" {
  description = "Numeric Google Cloud project number used in principal identifiers."
  type        = string
}

variable "billing_account" {
  description = "Bare billing account ID managed by Terraform."
  type        = string
}

variable "state_bucket_name" {
  description = "Terraform state bucket used by GitHub Actions."
  type        = string
}

variable "github_repository" {
  description = "GitHub repository in owner/name form."
  type        = string
}

variable "github_repository_id" {
  description = "Immutable GitHub repository ID. When set, it replaces the name-based provider admission condition."
  type        = string
  default     = ""
}

variable "name_prefix" {
  description = "Prefix for CI service accounts."
  type        = string
}

variable "runtime_service_account_emails" {
  description = "Runtime identities the deployment service account may attach to Cloud Run resources."
  type        = set(string)
}
