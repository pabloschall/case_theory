variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "instance_name" {
  type = string
}

variable "database_name" {
  type = string
}

variable "network_id" {
  type = string
}

variable "tier" {
  type    = string
  default = "db-g1-small"
}

variable "deletion_protection" {
  type    = bool
  default = true
}

variable "labels" {
  type    = map(string)
  default = {}
}
