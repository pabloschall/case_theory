variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "bucket_name" {
  type = string
}

variable "cors_origins" {
  type    = list(string)
  default = []
}

variable "labels" {
  type    = map(string)
  default = {}
}
