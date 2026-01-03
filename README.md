# searchMS

Search service for PersonalCook.

---

## Overview

SearchMS provides recipe search, explore, feed, and saved views backed by Elasticsearch. It also proxies user search to the user service.

---

## Architecture

- **FastAPI** application
- **Elasticsearch** for indexing and retrieval
- **JWT-based auth** for protected endpoints (feed/saved/my-recipes)
- **Downstream service calls**
  - **User service** for user search and user data
  - **Social service** for saved/follow context
- **Prometheus / Grafana** for metrics and monitoring
- **EFK stack (Fluent Bit, Elasticsearch, Kibana)** for centralized logging

---

## Configuration

The application configuration is fully separated from the implementation and is provided via multiple sources:

1. **Kubernetes Secrets**
   - Sensitive values such as JWT secret and Elasticsearch credentials.
2. **Helm values**
   - All configuration values are parameterized via Helm `values.yaml` files.

---

## Environment Variables

| Variable               | Description                    |
| ---------------------- | ------------------------------ |
| JWT_SECRET             | JWT signing secret             |
| JWT_ALGORITHM          | JWT algorithm (default: HS256) |
| SOCIAL_SERVICE_URL     | Social service base URL        |
| USER_SERVICE_URL       | User service base URL          |
| ELASTICSEARCH_HOST     | Elasticsearch endpoint         |
| ELASTICSEARCH_USER     | Elasticsearch user             |
| ELASTICSEARCH_PASSWORD | Elasticsearch password         |

---

## Local development

- Configuration via `.env` file (see `.env.example`)
- API available at: `http://localhost:8002`
- Elasticsearch available at: `http://localhost:9200` (if running locally)

1. docker network create personalcook-net
2. copy .env.example .env
3. docker compose up --build

---

## Kubernetes

- Configuration via Helm values, ConfigMaps, and Secrets
- API exposed through reverse proxy: http://134.112.152.8/api/search/
- Observability via `/metrics` endpoint

Separate Helm values files are used:

- `values-dev.yaml`
- `values-prod.yaml`

Example deployment:

helm upgrade --install search-service . -n personalcook -f values-prod.yaml

---

## Observability & Logging

The Recipe Service is integrates with a centralized logging and monitoring stack.

### Logging (EFK stack)

Application logs are written to stdout and collected at the Kubernetes level using:

- **Fluent Bit** – log collection and forwarding
- **Elasticsearch** – centralized log storage and indexing
- **Kibana** – log visualization and analysis

### Metrics & Monitoring

The service exposes Prometheus-compatible metrics at: /metrics

Metrics are scraped using:

- **Prometheus Operator** via a `ServiceMonitor`
- Visualized in **Grafana**

#### Exposed metrics

- **`http_requests_total`** _(Counter)_  
  Total number of HTTP requests.  
  **Labels:** `method`, `endpoint`, `status_code`

- **`http_request_errors_total`** _(Counter)_  
  Total number of failed HTTP requests (error responses).  
  **Labels:** `method`, `endpoint`, `status_code`

- **`http_request_latency_seconds`** _(Histogram)_  
  HTTP request latency distribution (seconds).  
  **Labels:** `method`, `endpoint`

- **`http_requests_in_progress`** _(Gauge)_  
  Number of HTTP requests currently being processed.

- **`search_queries_total`** _(Counter)_  
  Total number of search queries.  
  **Labels:** source, status

- **`search_results_returned`** _(Histogram)_  
  Distribution of the number of results returned per search query.  
  **Labels:** source, status

---

## Dependencies

- social service at SOCIAL_SERVICE_URL (default http://social_service:8000)
- user service at USER_SERVICE_URL (default http://user_service:8000/users)

---

## API Docs

- Swagger UI: http://134.112.152.8/api/search/docs
- ReDoc: http://134.112.152.8/api/search/redoc
- OpenAPI JSON: http://134.112.152.8/api/search/openapi.json

---

## Testing

Run tests locally:

```
pytest
```

---

## CI

This repo runs two GitHub Actions jobs:

- `test`: installs requirements and runs `pytest`
- `container`: builds the Docker image, starts Elasticsearch, runs the container, and hits `/` for a smoke test

Tests (files and intent):

- `tests/test_search_routes.py`: search endpoints for feed/explore/saved/users, with mocked ES and downstream services.

---

## Troubleshooting

- Elasticsearch connection errors: verify `ELASTICSEARCH_HOST` and credentials.
- JWT errors: verify `JWT_SECRET` and `JWT_ALGORITHM`.
- Downstream service errors: verify `SOCIAL_SERVICE_URL` and `USER_SERVICE_URL`.
