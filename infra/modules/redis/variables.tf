variable "project_id" {
  type = string
}

variable "region" {
  type = string
}

variable "instance_name" {
  type = string
}

variable "network_id" {
  type = string
}

variable "memory_size_gb" {
  type    = number
  default = 1
}

variable "labels" {
  type    = map(string)
  default = {}
}
