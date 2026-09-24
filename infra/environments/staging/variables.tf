variable "project_id" {
  description = "Google Cloud staging project ID."
  type        = string
  default     = "case-theory"
}

variable "region" {
  description = "Region for all staging resources."
  type        = string
  default     = "us-central1"
}

variable "project_number" {
  description = "Numeric Google Cloud staging project number."
  type        = string
  default     = "1062432609767"
}

variable "billing_account" {
  description = "Bare billing account ID used for the staging budget."
  type        = string
  default     = "01CBFB-A532AA-16BDDE"
}

variable "monthly_budget_usd" {
  description = "Monthly staging budget alert amount. This is an alert, not a spending cap."
  type        = number
  default     = 50
}

variable "frontend_origin" {
  description = "Public HTTPS origin allowed to upload directly to the evidence bucket. Leave empty until staging DNS is selected."
  type        = string
  default     = ""

  validation {
    condition     = var.frontend_origin == "" || can(regex("^https://", var.frontend_origin))
    error_message = "frontend_origin must be empty or start with https://."
  }
}

variable "enable_cloud_sql" {
  description = "Create the recurring-cost Cloud SQL staging instance."
  type        = bool
  default     = false
}

variable "enable_redis" {
  description = "Create the recurring-cost Memorystore staging instance."
  type        = bool
  default     = false
}

variable "cloud_sql_tier" {
  description = "Cloud SQL machine tier used after enable_cloud_sql is set."
  type        = string
  default     = "db-g1-small"
}

variable "redis_memory_size_gb" {
  description = "Memorystore capacity used after enable_redis is set."
  type        = number
  default     = 1

  validation {
    condition     = var.redis_memory_size_gb >= 1
    error_message = "redis_memory_size_gb must be at least 1."
  }
}

variable "github_repository" {
  description = "GitHub repository authorized to use Workload Identity Federation."
  type        = string
  default     = "pabloschall/case_theory"
}

variable "github_repository_id" {
  description = "Immutable numeric GitHub repository ID. Leave empty until it can be read through authenticated GitHub access."
  type        = string
  default     = ""
}
