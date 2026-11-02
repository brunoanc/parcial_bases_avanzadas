terraform {
  required_version = ">= 1.5"

  backend "gcs" {
    prefix = "dependencyguard"
  }

  required_providers {
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 7.0"
    }
  }
}

provider "google-beta" {
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}

provider "google-beta" {
  alias                 = "bootstrap"
  project               = var.project_id
  user_project_override = false
}

resource "google_project_service" "services" {
  provider = google-beta.bootstrap
  for_each = toset([
    "serviceusage.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "iam.googleapis.com",
    "run.googleapis.com",
    "artifactregistry.googleapis.com",
    "secretmanager.googleapis.com",
    "firebase.googleapis.com",
    "firebasehosting.googleapis.com",
    "identitytoolkit.googleapis.com",
  ])

  service            = each.key
  disable_on_destroy = false
}

resource "google_artifact_registry_repository" "images" {
  provider      = google-beta
  location      = var.region
  repository_id = "dependencyguard"
  format        = "DOCKER"

  depends_on = [google_project_service.services]
}

resource "google_service_account" "backend" {
  provider   = google-beta
  account_id = "dependencyguard-api"

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret" "neo4j_password" {
  provider  = google-beta
  secret_id = "dependencyguard-neo4j-password"

  replication {
    auto {}
  }

  depends_on = [google_project_service.services]
}

resource "google_secret_manager_secret_iam_member" "backend" {
  provider  = google-beta
  secret_id = google_secret_manager_secret.neo4j_password.id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.backend.email}"
}

resource "google_cloud_run_v2_service" "backend" {
  provider             = google-beta
  name                 = "dependencyguard-api"
  location             = var.region
  invoker_iam_disabled = false

  template {
    service_account = google_service_account.backend.email

    scaling {
      min_instance_count = 0
      max_instance_count = 1
    }

    containers {
      image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.images.repository_id}/backend:${var.image_tag}"

      ports {
        container_port = 8080
      }

      env {
        name  = "NEO4J_URI"
        value = var.neo4j_uri
      }

      env {
        name  = "NEO4J_USERNAME"
        value = var.neo4j_username
      }

      env {
        name  = "NEO4J_DATABASE"
        value = var.neo4j_database
      }

      env {
        name = "NEO4J_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.neo4j_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }

  depends_on = [google_secret_manager_secret_iam_member.backend]
}

resource "google_firebase_project" "app" {
  provider = google-beta

  depends_on = [google_project_service.services]
}

resource "google_firebase_web_app" "frontend" {
  provider     = google-beta
  project      = google_firebase_project.app.project
  display_name = "DependencyGuard"
}

resource "google_firebase_hosting_site" "frontend" {
  provider = google-beta
  project  = google_firebase_project.app.project
  site_id  = var.site_id
  app_id   = google_firebase_web_app.frontend.app_id
}

resource "google_identity_platform_config" "auth" {
  provider = google-beta
  project  = google_firebase_project.app.project

  authorized_domains = [
    "localhost",
    "${var.project_id}.firebaseapp.com",
    "${var.site_id}.firebaseapp.com",
    "${var.site_id}.web.app",
  ]
}
