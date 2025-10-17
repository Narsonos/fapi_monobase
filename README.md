# FastAPI application template (monolith)
This repo contains a template of a FastAPI monolith application that can be extended as a project it is used for needs. 

For monitoring/observability module:

👉 [See this repo](https://github.com/Narsonos/warden)

## This repo contains:
- FastAPI, MySQL, Redis, Nginx - core of the project.
- Celery and beat (though not used) - there's a config and CeleryTaskProcessor wrapper for convenience and loose coupling.
- User and Auth services, 4-layer architecture, caching.
- Github Actions workflows for automated deployment with a python script for simple Blue-Green deployment.
- Tests - unit, e2e, integration. ~98% coverage. There's a couple of very simple k6 tests.
- MySQL pre-baked image builder - makes tests run quicker!


## Table of expected ENV Variables (see github workflow files)
If the template is deployed without Github Actions workflow, but rather directly with the compose files - it is important to provide ENV values using according files:
 - .env (as prod)
 - .env.dev (for dev compose)
 - .env.test (for test compose). Database username/passwords get baked into the used MYSQL image when you run mysql_builder - please, be aware of that.

Otherwise, if Github Actions workflow is used - all envs are set there, refer to the table below.
Additional configuration can be provided in ./services/api/app/common/config.py


| Variable                 | Source                           | Meaning / Purpose                                                                                  |
| ------------------------ | -------------------------------- | -------------------------------------------------------------------------------------------------- |
| `GIT_COMMIT`             | `github.sha`                     | The Git commit hash of the current commit. Used for versioning/tagging Docker images.              |
| `APP_NAME`               | `env.SERVICE_NAME`               | The name of the service or application. Used as container_name prefix.                             |
| `DEFAULT_ADMIN_USERNAME` | `secrets.DEFAULT_ADMIN_USERNAME` | Default administrator username, (default = "admin"), added if no admin exists on startup.          |
| `DEFAULT_ADMIN_PASSWORD` | `secrets.DEFAULT_ADMIN_PASSWORD` | Default administrator password for the application, used during initial setup.                     |
| `ACCESS_SECRET`          | `secrets.ACCESS_SECRET`          | Secret key used to sign access tokens.                                                             |
| `REFRESH_SECRET`         | `secrets.REFRESH_SECRET`         | Secret key used to sign refresh tokens.                                                            |
| `MYSQL_ROOT_PASSWORD`    | `secrets.MYSQL_ROOT_PASSWORD`    | Root password for MySQL.                                                                           |
| `MYSQL_USER`             | `secrets.MYSQL_USER`             | Username for a MySQL user used by the application.                                                 |
| `MYSQL_PASSWORD`         | `secrets.MYSQL_PASSWORD`         | Password for the MySQL user.                                                                       |
| `MYSQL_DATABASE`         | `secrets.MYSQL_DATABASE`         | Name of the MySQL database the application connects to.                                            |
| `REDIS_PASS`             | `secrets.REDIS_PASS`             | Password for Redis if authentication is enabled.                                                   |
| `OTEL_GRPC_HOST`         | `secrets.OTEL_GRPC_HOST`         | Hostname and port of an OTel-collector to which the service will export metrics and traces.        |
| `OTEL_SERVICE_NAME`      | `secrets.OTEL_SERVICE_NAME`      | Serves as a value for 'service.name' tag in opentelemetry, for distinguishing services             |
