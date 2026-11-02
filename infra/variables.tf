variable "project_id" {
  type = string
}

variable "site_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "image_tag" {
  type    = string
  default = "v1"
}

variable "neo4j_uri" {
  type = string
}

variable "neo4j_username" {
  type    = string
  default = "neo4j"
}

variable "neo4j_database" {
  type    = string
  default = ""
}
