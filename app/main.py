from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import search
from app.elastic.index_setup import setup_indices

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

#ali to še rabimo? ni mi uspel prevert - PREVERI
@app.get("/")
def root():
    return {"msg": "Search Service running in Docker!"}
