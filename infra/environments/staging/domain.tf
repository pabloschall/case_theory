locals {
  custom_domain_enabled = var.custom_domain != ""
}

resource "google_compute_global_address" "frontend" {
  count = local.custom_domain_enabled ? 1 : 0

  project = var.project_id
  name    = "${local.name_prefix}-frontend-ip"
}

resource "google_compute_region_network_endpoint_group" "frontend" {
  count = local.custom_domain_enabled ? 1 : 0

  project               = var.project_id
  name                  = "${local.name_prefix}-frontend-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"

  cloud_run {
    service = "${local.name_prefix}-frontend"
  }
}

resource "google_compute_backend_service" "frontend" {
  count = local.custom_domain_enabled ? 1 : 0

  project               = var.project_id
  name                  = "${local.name_prefix}-frontend-backend"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL_MANAGED"

  backend {
    group = google_compute_region_network_endpoint_group.frontend[0].id
  }

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_managed_ssl_certificate" "frontend" {
  count = local.custom_domain_enabled ? 1 : 0

  project = var.project_id
  name    = "${local.name_prefix}-frontend-cert"

  managed {
    domains = [var.custom_domain, "www.${var.custom_domain}"]
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "google_compute_url_map" "frontend" {
  count = local.custom_domain_enabled ? 1 : 0

  project         = var.project_id
  name            = "${local.name_prefix}-frontend-https"
  default_service = google_compute_backend_service.frontend[0].id
}

resource "google_compute_target_https_proxy" "frontend" {
  count = local.custom_domain_enabled ? 1 : 0

  project          = var.project_id
  name             = "${local.name_prefix}-frontend-https"
  url_map          = google_compute_url_map.frontend[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend[0].id]
}

resource "google_compute_global_forwarding_rule" "frontend_https" {
  count = local.custom_domain_enabled ? 1 : 0

  project               = var.project_id
  name                  = "${local.name_prefix}-frontend-https"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.frontend[0].address
  port_range            = "443"
  target                = google_compute_target_https_proxy.frontend[0].id
}

resource "google_compute_url_map" "frontend_http_redirect" {
  count = local.custom_domain_enabled ? 1 : 0

  project = var.project_id
  name    = "${local.name_prefix}-frontend-http-redirect"

  default_url_redirect {
    https_redirect = true
    strip_query    = false
  }
}

resource "google_compute_target_http_proxy" "frontend_redirect" {
  count = local.custom_domain_enabled ? 1 : 0

  project = var.project_id
  name    = "${local.name_prefix}-frontend-http-redirect"
  url_map = google_compute_url_map.frontend_http_redirect[0].id
}

resource "google_compute_global_forwarding_rule" "frontend_http" {
  count = local.custom_domain_enabled ? 1 : 0

  project               = var.project_id
  name                  = "${local.name_prefix}-frontend-http"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  ip_address            = google_compute_global_address.frontend[0].address
  port_range            = "80"
  target                = google_compute_target_http_proxy.frontend_redirect[0].id
}
