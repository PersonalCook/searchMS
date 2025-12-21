CI overview

This repo runs two GitHub Actions jobs:
- test: installs requirements and runs `pytest`
- container: builds the Docker image, starts Elasticsearch, runs the container, and hits `/` for a smoke test

Tests (files and intent):
- `tests/test_search_routes.py`: search endpoints for feed/explore/saved/users, with mocked ES and downstream services.
