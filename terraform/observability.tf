variable "alert_email" {
  type        = string
  sensitive   = true
  description = "Team mailbox that receives MetroAI Cloud Monitoring incidents."
}

locals {
  app_container = join(" AND ", [
    "resource.type = \"k8s_container\"",
    "resource.labels.cluster_name = \"metroai-gke\"",
    "resource.labels.namespace_name = \"metroai\"",
    "resource.labels.container_name = \"app\"",
  ])

  server_errors = "logging.googleapis.com/user/${google_logging_metric.http_5xx.name}"

  dashboard_metrics = [
    {
      title   = "HTTP 5xx responses per minute"
      type    = local.server_errors
      aligner = "ALIGN_SUM"
      unit    = "responses"
    },
    {
      title   = "Application CPU usage"
      type    = "kubernetes.io/container/cpu/core_usage_time"
      aligner = "ALIGN_RATE"
      unit    = "CPU cores"
    },
    {
      title   = "Application memory usage"
      type    = "kubernetes.io/container/memory/used_bytes"
      aligner = "ALIGN_MEAN"
      unit    = "bytes"
    },
  ]
}

resource "google_logging_metric" "http_5xx" {
  name        = "metroai_http_5xx"
  description = "One count per MetroAI application request log with a final HTTP status from 500 to 599."
  filter      = <<-FILTER
    ${local.app_container}
    log_id("stdout")
    jsonPayload.event="http_request"
    jsonPayload.status_code>=500
    jsonPayload.status_code<600
  FILTER

  metric_descriptor {
    metric_kind = "DELTA"
    value_type  = "INT64"
    unit        = "1"
  }
}

resource "google_monitoring_dashboard" "metroai" {
  dashboard_json = jsonencode({
    displayName = "MetroAI service health"
    mosaicLayout = {
      columns = 12
      # The Dashboard API omits zero coordinates from its response.
      tiles = [for index, metric in local.dashboard_metrics : merge(
        index == 2 ? { xPos = 6 } : {},
        index == 0 ? {} : { yPos = 4 },
        {
          width  = index == 0 ? 12 : 6
          height = 4
          widget = {
            title = metric.title
            xyChart = {
              yAxis = { label = metric.unit, scale = "LINEAR" }
              dataSets = [{
                plotType = "LINE"
                timeSeriesQuery = {
                  timeSeriesFilter = {
                    filter = "metric.type = \"${metric.type}\" AND ${local.app_container}"
                    aggregation = {
                      alignmentPeriod    = "60s"
                      perSeriesAligner   = metric.aligner
                      crossSeriesReducer = "REDUCE_SUM"
                    }
                  }
                }
              }]
            }
          }
        }
      )]
    }
  })
}

resource "google_monitoring_notification_channel" "team_email" {
  display_name = "MetroAI team email"
  type         = "email"
  labels       = { email_address = var.alert_email }
}

resource "google_monitoring_alert_policy" "http_5xx" {
  display_name          = "MetroAI HTTP 5xx burst"
  combiner              = "OR"
  enabled               = true
  notification_channels = [google_monitoring_notification_channel.team_email.name]

  conditions {
    display_name = "At least 3 app HTTP 5xx responses in a minute"
    condition_threshold {
      filter          = "metric.type = \"${local.server_errors}\" AND ${local.app_container}"
      comparison      = "COMPARISON_GT"
      threshold_value = 2
      duration        = "0s"

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_SUM"
        cross_series_reducer = "REDUCE_SUM"
      }

      trigger {
        count = 1
      }
    }
  }

  alert_strategy {
    auto_close           = "1800s"
    notification_prompts = ["OPENED"]
  }

  documentation {
    mime_type = "text/markdown"
    content   = "Inspect MetroAI request logs and check HTTPS readiness. Compare the request times with recent GitHub Actions deployments."
  }
}
