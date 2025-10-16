# FastAPI application template (monolith)
This repo contains a template of a FastAPI monolith application that can be extended as a project it is used for needs.

Contains:
- FastAPI, MySQL, Redis, Nginx - core of the project.
- Celery and beat (though not used) - there's a config and CeleryTaskProcessor wrapper for convenience and loose coupling.
- User and Auth services, 4-layer architecture, caching.
- Grafana, Loki, Promtail, Prometheus, Tempo, Alertmanager. All provisioned and with basic dashboards implemented. Opentelemetry as metrics/traces format.
- Github Actions workflows for automated deployment with a python script for simple Blue-Green deployment.
- Tests - unit, e2e, integration. ~98% coverage.
- MySQL pre-baked image builder - makes tests run quicker!

Todo:
- Deployment .yml for monitoring

Notes:
- Observability subsystem is written in a manner that expects its setup separate from the main application