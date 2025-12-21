import os

import jwt

from app.routers import search as search_router


def _auth_headers(user_id=1):
    token = jwt.encode(
        {"user_id": user_id},
        os.environ["JWT_SECRET"],
        algorithm=os.environ["JWT_ALGORITHM"],
    )
    return {"Authorization": f"Bearer {token}"}


def test_feed_requires_auth(client):
    response = client.get("/search/feed")
    assert response.status_code == 401


def test_feed_returns_results(client, monkeypatch):
    async def fake_get_following(token):
        return [{"following_id": 2}]

    async def fake_search(**kwargs):
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "10",
                        "_score": 1.0,
                        "_source": {"recipe_name": "Soup", "user_id": 2},
                    }
                ]
            }
        }

    monkeypatch.setattr(search_router, "get_following", fake_get_following)
    monkeypatch.setattr(search_router.client, "search", fake_search)

    response = client.get("/search/feed", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["id"] == "10"


def test_explore_returns_results(client, monkeypatch):
    async def fake_search(**kwargs):
        return {"hits": {"hits": []}}

    monkeypatch.setattr(search_router.client, "search", fake_search)

    response = client.get("/search/explore")
    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_saved_requires_auth(client):
    response = client.get("/search/saved")
    assert response.status_code == 401


def test_saved_returns_results(client, monkeypatch):
    async def fake_get_saved(token):
        return [{"recipe_id": 5}]

    async def fake_get_following(token):
        return [3]

    async def fake_search(**kwargs):
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "5",
                        "_score": 1.0,
                        "_source": {"recipe_name": "Pasta", "recipe_id": 5},
                    }
                ]
            }
        }

    monkeypatch.setattr(search_router, "get_saved", fake_get_saved)
    monkeypatch.setattr(search_router, "get_following", fake_get_following)
    monkeypatch.setattr(search_router.client, "search", fake_search)

    response = client.get("/search/saved", headers=_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["results"][0]["id"] == "5"


def test_users_search_proxies_to_user_service(client, monkeypatch):
    async def fake_user_search(q, skip=0, limit=20):
        return [{"user_id": 1, "username": "ana"}]

    monkeypatch.setattr(search_router, "user_search", fake_user_search)

    response = client.get("/search/users", params={"q": "an"})
    assert response.status_code == 200
    assert response.json()[0]["username"] == "ana"
