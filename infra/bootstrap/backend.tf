terraform {
  backend "gcs" {
    bucket = "case-theory-tf-state"
    prefix = "bootstrap"
  }
}
