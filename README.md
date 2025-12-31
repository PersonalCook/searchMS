# searchMS

Search service for PersonalCook.

## Overview
SearchMS provides recipe search, explore, feed, and saved views backed by Elasticsearch. It also proxies user search to the user service.

## Architecture
- FastAPI service with Elasticsearch as the primary data store for search.
- Uses JWT auth for feed/saved/my-recipes queries.
- Calls social and user services for follow/saved data and user search.

## Local dev
1. docker network create personalcook-net
2. copy .env.example .env
3. docker compose up --build

## Configuration
Environment variables (see `.env.example`):
- `JWT_SECRET`, `JWT_ALGORITHM`: JWT validation for protected endpoints.
- `SOCIAL_SERVICE_URL`: social service base URL.
- `USER_SERVICE_URL`: user service base URL.
- `ELASTICSEARCH_HOST`: Elasticsearch base URL.
- `ELASTICSEARCH_USER`, `ELASTICSEARCH_PASSWORD`: Elasticsearch credentials.

## Dependencies
- social service at SOCIAL_SERVICE_URL (default http://social_service:8000)
- user service at USER_SERVICE_URL (default http://user_service:8000/users)

## Ports
- API: 8002
- Elasticsearch: 9200

## API Docs
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc
- OpenAPI JSON: http://localhost:8002/openapi.json

## Testing
Run tests locally:
```
pytest
```

## CI
This repo runs two GitHub Actions jobs:
- `test`: installs requirements and runs `pytest`
- `container`: builds the Docker image, starts Elasticsearch, runs the container, and hits `/` for a smoke test

Tests (files and intent):
- `tests/test_search_routes.py`: search endpoints for feed/explore/saved/users, with mocked ES and downstream services.

## Deployment
- Docker image and Helm chart are provided for deployment.
- Health check: `GET /health`.

## Troubleshooting
- Elasticsearch connection errors: verify `ELASTICSEARCH_HOST` and credentials.
- JWT errors: verify `JWT_SECRET` and `JWT_ALGORITHM`.
- Downstream service errors: verify `SOCIAL_SERVICE_URL` and `USER_SERVICE_URL`.
