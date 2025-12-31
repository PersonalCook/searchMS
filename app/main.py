from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search
from app.elastic.index_setup import setup_indices

from .metrics import (
    num_requests,
    num_errors,
    request_latency,
    requests_in_progress
)
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response
import time
from app.schemas import RootResponse, HealthResponse

app = FastAPI(title="Search Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await setup_indices()

app.include_router(search.router)

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    method = request.method
    endpoint = request.url.path

    requests_in_progress.inc()
    start_time = time.time()

    try:
        response = await call_next(request)
        status_code = response.status_code
        duration = time.time() - start_time

        num_requests.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

        if status_code >= 400:
            num_errors.labels(method=method, endpoint=endpoint, status_code=status_code).inc()

        request_latency.labels(method=method, endpoint=endpoint).observe(duration)

        return response
    finally:
        requests_in_progress.dec()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
 
@app.get("/")
@app.get(
    "/",
    response_model=RootResponse,
    summary="Service info",
    responses={
        200: {
            "description": "OK",
            "content": {"application/json": {"example": {"msg": "Search Service running!"}}},
        }
    },
)
def root():
    return {"msg": "Search Service running!"}

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    responses={
        200: {"description": "OK", "content": {"application/json": {"example": {"status": "ok"}}}}
    },
)
def health():
    return {"status": "ok"}
