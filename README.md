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
