from fastapi import APIRouter, Depends, HTTPException, status, Query, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
import httpx
from ..elastic.client import client
from ..services.social_client import get_following, get_saved 
from ..services.user_client import search_users as user_search
from ..utils.auth import decode_jwt
from ..schemas import ErrorResponse, SearchResults, UserSummary
from ..metrics import search_queries, search_results_returned

router = APIRouter(prefix="/search", tags=["Search"])
bearer = HTTPBearer(auto_error=False)

EXAMPLE_RESULTS = {
    "results": [
        {
            "id": "10",
            "score": 1.0,
            "recipe": {
                "recipe_id": 10,
                "recipe_name": "Soup",
                "user_id": 2,
                "visibility": "public",
                "category": "soup",
                "total_time": 30,
            },
        }
    ]
}

EXAMPLE_USERS = [{"user_id": 1, "username": "ana"}]

ERROR_401 = {
    "model": ErrorResponse,
    "description": "Unauthorized",
    "content": {"application/json": {"example": {"detail": "Invalid token"}}},
}

ERROR_500 = {
    "model": ErrorResponse,
    "description": "Internal error",
    "content": {"application/json": {"example": {"detail": "Internal server error"}}},
}

def normalize_following_ids(following):
    if not following:
        return []
    if isinstance(following[0], dict):
        return [int(f["following_id"]) for f in following if "following_id" in f]
    return [int(x) for x in following]

def normalize_saved_recipe_ids(saved): 
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
        raise HTTPException(status_code=401, detail=str(e))


#filter for posts by people you follow (za FEED)
@router.get(
    "/feed",
    response_model=SearchResults,
    summary="Search feed recipes",
    description="Returns public and followers-only recipes from users the viewer follows.",
    responses={
        200: {"description": "OK", "content": {"application/json": {"example": EXAMPLE_RESULTS}}},
        401: ERROR_401,
        422: {"description": "Validation error"},
        500: ERROR_500,
    },
)
async def search_recipes_feed(
    user_token = Depends(get_user_and_token_optional),
    skip: int = Query(0, ge=0, description="Number of items to skip", examples={"example": {"value": 0}}),
    limit: int = Query(20, ge=1, le=100, description="Max items to return", examples={"example": {"value": 20}}),
):

    viewer_id, token = user_token
    if token is None:
        raise HTTPException(status_code=401, detail="Feed available only when logged in")
    following = normalize_following_ids(await get_following(token))
    if not following:
        search_queries.labels(source="feed", status="success").inc()
        search_results_returned.labels(source="feed", status="success").observe(0)
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
    search_queries.labels(source="feed", status="success").inc()
    search_results_returned.labels(source="feed", status="success").observe(len(results))
    return {"results": results}


#filter for all public recepies and recipes by people you follow + filtering (za EXPLORE page)
@router.get(
    "/explore",
    response_model=SearchResults,
    summary="Search explore recipes",
    description="Returns public recipes and, if logged in, followed users' recipes.",
    responses={
        200: {"description": "OK", "content": {"application/json": {"example": EXAMPLE_RESULTS}}},
        401: ERROR_401,
        422: {"description": "Validation error"},
        500: ERROR_500,
    },
)
async def search_recipes_explore(
    user_token = Depends(get_user_and_token_optional),
    q: str | None = Query(
        None,
        description="Full-text query across name/description/ingredients/keywords/category",
        examples={"example": {"value": "pasta"}},
    ),
    category: str | None = Query(
        None,
        description="Filter by category",
        examples={"example": {"value": "italian"}},
    ),
    max_time: int | None = Query(
        None,
        ge=1,
        description="Filter by maximum total time (minutes)",
        examples={"example": {"value": 45}},
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip", examples={"example": {"value": 0}}),
    limit: int = Query(20, ge=1, le=100, description="Max items to return", examples={"example": {"value": 20}}),
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
        search_queries.labels(source="explore", status="success").inc()
        search_results_returned.labels(source="explore", status="success").observe(len(results))
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
    search_queries.labels(source="explore", status="success").inc()
    search_results_returned.labels(source="explore", status="success").observe(len(results))
    return {"results": results}

#filter for saved recipes and own recipes + filtering (za SAVED page)
@router.get(
    "/saved",
    response_model=SearchResults,
    summary="Search saved recipes",
    description="Returns saved recipes visible to the viewer with optional filters.",
    responses={
        200: {"description": "OK", "content": {"application/json": {"example": EXAMPLE_RESULTS}}},
        401: ERROR_401,
        422: {"description": "Validation error"},
        500: ERROR_500,
    },
)
async def search_recipes_saved(
    user_token = Depends(get_user_and_token_optional),
    q: str | None = Query(
        None,
        description="Full-text query across name/description/ingredients/keywords/category",
        examples={"example": {"value": "soup"}},
    ),
    category: str | None = Query(
        None,
        description="Filter by category",
        examples={"example": {"value": "vegan"}},
    ),
    max_time: int | None = Query(
        None,
        ge=1,
        description="Filter by maximum total time (minutes)",
        examples={"example": {"value": 30}},
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip", examples={"example": {"value": 0}}),
    limit: int = Query(20, ge=1, le=100, description="Max items to return", examples={"example": {"value": 20}}),
):

    must = []
    filters = []
    viewer_id, token = user_token
    if token is None:
        raise HTTPException(status_code=401, detail="Saved recipes available only when logged in")

    saved = normalize_saved_recipe_ids(await get_saved(token))
    following = normalize_following_ids(await get_following(token))

    if not saved:
        search_queries.labels(source="saved", status="success").inc()
        search_results_returned.labels(source="saved", status="success").observe(0)
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
    search_queries.labels(source="saved", status="success").inc()
    search_results_returned.labels(source="saved", status="success").observe(len(results))
    return {"results": results}


#filter for own recipes + filtering (za MY RECIPES page)
@router.get(
    "/my_recipes",
    response_model=SearchResults,
    summary="Search my recipes",
    description="Returns viewer's own recipes with optional filters.",
    responses={
        200: {"description": "OK", "content": {"application/json": {"example": EXAMPLE_RESULTS}}},
        401: ERROR_401,
        422: {"description": "Validation error"},
        500: ERROR_500,
    },
)
async def search_my_recipes(
    user_token = Depends(get_user_and_token_optional),
    q: str | None = Query(
        None,
        description="Full-text query across name/description/ingredients/keywords/category",
        examples={"example": {"value": "cake"}},
    ),
    category: str | None = Query(
        None,
        description="Filter by category",
        examples={"example": {"value": "dessert"}},
    ),
    max_time: int | None = Query(
        None,
        ge=1,
        description="Filter by maximum total time (minutes)",
        examples={"example": {"value": 60}},
    ),
    skip: int = Query(0, ge=0, description="Number of items to skip", examples={"example": {"value": 0}}),
    limit: int = Query(20, ge=1, le=100, description="Max items to return", examples={"example": {"value": 20}}),
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
    search_queries.labels(source="my_recipes", status="success").inc()
    search_results_returned.labels(source="my_recipes", status="success").observe(len(results))
    return {"results": results}


@router.get(
    "/users",
    response_model=list[UserSummary],
    summary="Search users",
    description="Proxies user search to the user service.",
    responses={
        200: {"description": "OK", "content": {"application/json": {"example": EXAMPLE_USERS}}},
        422: {"description": "Validation error"},
        500: ERROR_500,
    },
)
async def search_users(
    q: str = Query(..., description="Query for usernames", examples={"example": {"value": "an"}}),
    skip: int = Query(0, ge=0, description="Number of items to skip", examples={"example": {"value": 0}}),
    limit: int = Query(20, ge=1, le=100, description="Max items to return", examples={"example": {"value": 20}}),
):
    results = await user_search(q=q, skip=skip, limit=limit)
    search_queries.labels(source="users", status="success").inc()
    search_results_returned.labels(source="users", status="success").observe(len(results))
    return results
