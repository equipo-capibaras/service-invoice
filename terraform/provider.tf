terraform {
  required_providers {
    google = {
      version = "~> 6.12.0"
    }
  }
}

# State is stored in a GCS bucket.
terraform {
  backend "gcs" {
    prefix = "service-invoice/state"
  }
}

# Configures the Google Cloud Platform provider.
provider "google" {
  project = local.project_id
  region  = local.region
}
