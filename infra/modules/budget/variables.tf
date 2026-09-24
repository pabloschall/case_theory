variable "billing_account" {
  description = "Bare billing account ID, such as 000000-000000-000000."
  type        = string
}

variable "project_number" {
  description = "Numeric Google Cloud project number used to scope the budget."
  type        = string
}

variable "display_name" {
  type = string
}

variable "monthly_amount_usd" {
  type = number

  validation {
    condition     = var.monthly_amount_usd > 0
    error_message = "monthly_amount_usd must be greater than zero."
  }
}
