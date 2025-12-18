from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import httpx
from ..elastic.client import client
from ..services.social_client import get_following, get_saved # TREBA ŠE NAREDIT !!
from ..services.user_client import search_users as user_search
from ..utils.auth import decode_jwt


router = APIRouter(prefix="/search", tags=["Search"])
bearer = HTTPBearer(auto_error=False)

def normalize_following_ids(following):
    # supports both: [ {"following_id": 6, ...}, ... ] and [6,7,...]
    if not following:
        return []
    if isinstance(following[0], dict):
        return [int(f["following_id"]) for f in following if "following_id" in f]
    return [int(x) for x in following]

def normalize_saved_recipe_ids(saved): #probaj brez tega, mogoče dela
    if not saved:
        return []
    if isinstance(saved[0], dict):
        return [int(x["recipe_id"]) for x in saved if "recipe_id" in x]
    return [int(x) for x in saved]



def get_user_and_token_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
):
    if credentials is None:
        return None, None
    try:
        payload = decode_jwt(credentials.credentials)
        return payload["user_id"], credentials.credentials
    except Exception as e:
        # invalid/expired token
        raise HTTPException(status_code=401, detail=str(e))


#filter for posts by people you follow (za FEED)
@router.get("/feed")
async def search_recipes_feed(
    user_token = Depends(get_user_and_token_optional),
    skip: int = 0,
    limit: int = 20):

    viewer_id, token = user_token
    if token is None:
        raise HTTPException(status_code=401, detail="Feed available only when logged in")
    following = normalize_following_ids(await get_following(token))
    if not following:
        return {"results": []}

    
    #query
    es_query = {
        "bool": {
            "must_not": [
                {"term": {"user_id": viewer_id}}  # exclude viewer's own recipes
            ],
            "should": [
                {
                    "bool": {
                        "must": [
                            {"terms": {"user_id": following}},
                            {"term": {"visibility": "public"}}
                        ]
                    }
                },
                {
                    "bool": {
                        "must": [
                            {"terms": {"user_id": following}},
                            {"term": {"visibility": "followers_only"}}
                        ]
                    }
                }
            ],
            "minimum_should_match": 1
        }
    }
    response = await client.search(
        index = "recipes",
        query = es_query,
        sort = [{"created_at":{"order":"desc"}}],
        from_=skip,
        size=limit
        )
    results = [
        {
            "id": hit["_id"],
            "score": hit["_score"],
            "recipe": hit["_source"],
        }
        for hit in response["hits"]["hits"]
    ]
    return {"results": results}


#filter for all public recepies and recipes by people you follow + filtering (za EXPLORE page)
@router.get("/explore")
async def search_recipes_explore(
    user_token = Depends(get_user_and_token_optional),
    q: str | None = None,
    category: str | None = None,
    max_time: int | None = None, 
    skip: int = 0,
    limit: int = 20
):
    viewer_id, token = user_token
    must = []
    filters = []
    following = []
    if token:
        following = normalize_following_ids(await get_following(token))
        visibility_block = {
            "bool": {
                "should": [
                    {"term": {"visibility": "public"}},
                    {
                        "bool": {
                            "must": [
                                {"terms": {"user_id": following}},
                                {"term": {"visibility": "followers_only"}}
                            ]
                        }
                    },
                    {"term": {"user_id": viewer_id}}
                ],
                "minimum_should_match": 1
            }
        }
        # hide viewer's own recipes in explore
        filters.append({"bool": {"must_not": [{"term": {"user_id": viewer_id}}]}})
    else:
        # unauthenticated users see only public recipes
        visibility_block = {"term": {"visibility": "public"}}
    filters.append(visibility_block)

    if not q and not category and not max_time:
        es_query = {
            "bool": {
                "filter": filters,
            }
        }
        response = await client.search(
            index = "recipes",
            query = es_query,
            sort = [{"created_at":{"order":"desc"}}],
            from_=skip,
            size=limit
        )
        results = [
            {
                "id": hit["_id"],
                "score": hit["_score"],
                "recipe": hit["_source"],
            }
            for hit in response["hits"]["hits"]
        ]
        return {"results": results}
    
    if q:
        must.append({
            "multi_match": {
                "query": q,
                "fields": [
                    "recipe_name^3",
                    "description",
                    "ingredients",
                    "keywords",
                    "category"
                ],
                "fuzziness": "AUTO"
            }
        })

    if category:
        filters.append({
            "term": {"category": category}
        })

    if max_time:
        filters.append({
            "range": {
                "total_time": {"lte": max_time}
            }
        })
    
    es_query = {
        "bool": {
            "must": must,
            "filter": filters,
        }
    }

    response = await client.search(
        index = "recipes",
        query = es_query,
        from_=skip,
        size=limit
    )
    results = [
        {
            "id": hit["_id"],
            "score": hit["_score"],
            "recipe": hit["_source"],
        }
        for hit in response["hits"]["hits"]
    ]
    return {"results": results}

#filter for saved recipes and own recipes + filtering (za SAVED page)
@router.get("/saved")
async def search_recipes_saved(
    user_token = Depends(get_user_and_token_optional),
    q: str | None = None,
    category: str | None = None,
    max_time: int | None = None, 
    skip: int = 0,
    limit: int = 20
):

    must = []
    filters = []
    viewer_id, token = user_token
    if token is None:
        raise HTTPException(status_code=401, detail="Saved recipes available only when logged in")

    saved = normalize_saved_recipe_ids(await get_saved(token))
    following = normalize_following_ids(await get_following(token))

    if not saved:
        return {"results": []}
    
    filters.append({
        "bool": {
            "should": [
                {
                    "bool": {
                        "must": [
                            {"term": {"visibility": "public"}},
                            {"terms": {"recipe_id": saved}}
                        ]
                    }
                },
                {
                    "bool": {
                        "must": [
                            {"term": {"visibility": "followers_only"}},
                            {"terms": {"user_id": following}},
                            {"terms": {"recipe_id": saved}}
                        ]
                    }
                },
                {
                    "bool": {
                        "must": [
                            {"term": {"visibility": "private"}},
                            {"term": {"user_id": viewer_id}}
                        ]
                    }
                }

            ]
        }
    })
    if q:
        must.append({
            "multi_match": {
                "query": q,
                "fields": [
                    "recipe_name^3",
                    "description",
                    "ingredients",
                    "keywords",
                    "category"
                ],
                "fuzziness": "AUTO"
            }
        })

    if category:
        filters.append({
            "term": {"category": category}
        })

    if max_time:
        filters.append({
            "range": {
                "total_time": {"lte": max_time}
            }
        })
    
    es_query = {
        "bool": {
            "must": must,
            "filter": filters,
        }
    }
    response = await client.search(
        index = "recipes",
        query = es_query,
        from_=skip,
        size=limit
    )
    results = [
        {
            "id": hit["_id"],
            "score": hit["_score"],
            "recipe": hit["_source"],
        }
        for hit in response["hits"]["hits"]
    ]
    return {"results": results}


   
#mybe še autocomplete

#filter for own recipes + filtering (za MY RECIPES page)
@router.get("/my_recipes")
async def search_my_recipes(
    user_token = Depends(get_user_and_token_optional),
    q: str | None = None,
    category: str | None = None,
    max_time: int | None = None, 
    skip: int = 0,
    limit: int = 20
):
    must = []
    filters = []
    sort = [{"created_at":{"order":"desc"}}]
    viewer_id, token = user_token
    if token is None:
        raise HTTPException(status_code=401, detail="My recipes available only when logged in")
    filters.append({"term": {"user_id": viewer_id}})

    if q:
        sort = None
        must.append({
            "multi_match": {
                "query": q,
                "fields": [
                    "recipe_name^3",
                    "description",
                    "ingredients",
                    "keywords",
                    "category"
                ],
                "fuzziness": "AUTO"
            }
        })

    if category:
        filters.append({
            "term": {"category": category}
        })
    if max_time:
        filters.append({
            "range": {
                "total_time": {"lte": max_time}
            }
        })
    es_query = {
        "bool": {
            "must": must,
            "filter": filters,
        }
    }
    response = await client.search(
        index = "recipes",
        query = es_query,
        from_=skip,
        size=limit
    )
    results = [
        {
            "id": hit["_id"],
            "score": hit["_score"],
            "recipe": hit["_source"],
        }
        for hit in response["hits"]["hits"]
    ]
    return {"results": results}


@router.get("/users")
async def search_users(
    q: str,
    skip: int = 0,
    limit: int = 20,
):
    return await user_search(q=q, skip=skip, limit=limit)
