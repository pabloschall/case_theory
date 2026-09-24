variable "project_id" {
  description = "Google Cloud project that owns the Terraform state bucket."
  type        = string
  default     = "case-theory"
}

variable "state_bucket_name" {
  description = "Globally unique bucket used by the Terraform GCS backend."
  type        = string
  default     = "case-theory-tf-state"
}

variable "state_bucket_location" {
  description = "Location for the Terraform state bucket."
  type        = string
  default     = "US"
}
