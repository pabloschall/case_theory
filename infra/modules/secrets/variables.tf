variable "project_id" {
  type = string
}

variable "secret_accessors" {
  description = "Map of secret ID to service-account email addresses allowed to read it."
  type        = map(set(string))
}

variable "labels" {
  type    = map(string)
  default = {}
}
