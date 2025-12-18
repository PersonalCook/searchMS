from .client import client

RECIPE_INDEX_SETTINGS = {
    "mappings": {
        "properties": {
            "recipe_name": {"type": "text"},
            "recipe_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "description": {"type": "text"},
            "ingredients": {"type": "text"},
            "cooking_time": {"type": "text"},
            "total_time": {"type": "text"},
            "keywords": {"type": "keyword"},
            "category": {"type": "keyword"},
            "visibility": {"type": "keyword"},
            "created_at": {"type": "date"}
        }
    }
}

async def setup_indices():
    exists = await client.indices.exists(index="recipes")
    if not exists:
        await client.indices.create(
            index="recipes",
            body=RECIPE_INDEX_SETTINGS
        )
