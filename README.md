# FastAPI application template (monolith)
This repo contains a template of a FastAPI monolith application that can be extended as a project it is used for needs. 

For monitoring/observability module:

👉 [See this repo](https://github.com/Narsonos/warden)

Contains:
- FastAPI, MySQL, Redis, Nginx - core of the project.
- Celery and beat (though not used) - there's a config and CeleryTaskProcessor wrapper for convenience and loose coupling.
- User and Auth services, 4-layer architecture, caching.
- Github Actions workflows for automated deployment with a python script for simple Blue-Green deployment.
- Tests - unit, e2e, integration. ~98% coverage. There's a couple of very simple k6 tests.
- MySQL pre-baked image builder - makes tests run quicker!
