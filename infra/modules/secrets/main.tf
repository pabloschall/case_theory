locals {
  accessor_bindings = flatten([
    for secret_id, members in var.secret_accessors : [
      for member in members : {
        key       = "${secret_id}:${member}"
        secret_id = secret_id
        member    = member
      }
    ]
  ])
}

resource "google_secret_manager_secret" "secret" {
  for_each = var.secret_accessors

  project   = var.project_id
  secret_id = each.key
  labels    = var.labels

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "accessor" {
  for_each = { for binding in local.accessor_bindings : binding.key => binding }

  project   = var.project_id
  secret_id = google_secret_manager_secret.secret[each.value.secret_id].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${each.value.member}"
}
