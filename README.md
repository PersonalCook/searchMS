# searchMS

Search service for PersonalCook.

## Local dev
1. docker network create personalcook-net
2. copy .env.example .env
3. docker compose up --build

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

## CI
This repo runs two GitHub Actions jobs:
- test: installs requirements and runs `pytest`
- container: builds the Docker image, starts Elasticsearch, runs the container, and hits `/` for a smoke test

Tests (files and intent):
- `tests/test_search_routes.py`: search endpoints for feed/explore/saved/users, with mocked ES and downstream services.
