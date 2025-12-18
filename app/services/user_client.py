import os, httpx

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL")
if not USER_SERVICE_URL:
    raise RuntimeError("USER_SERVICE_URL must be set")


async def search_users(q: str, skip: int = 0, limit: int = 20):
    url = f"{USER_SERVICE_URL}/search"
    params = {"q": q, "skip": skip, "limit": limit}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
