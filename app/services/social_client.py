import os, httpx

SOCIAL_SERVICE_URL = os.getenv("SOCIAL_SERVICE_URL")
if not SOCIAL_SERVICE_URL:
    raise RuntimeError("SOCIAL_SERVICE_URL must be set")

async def get_saved(token: str):
    url = f"{SOCIAL_SERVICE_URL}/saved/me"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()  # list of saved recipes

async def get_following(token: str):
    url = f"{SOCIAL_SERVICE_URL}/follows/following/me"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()
