import os
from elasticsearch import AsyncElasticsearch

ES_HOST = os.getenv("ELASTICSEARCH_HOST", "https://quickstart-es-http:9200")
ES_USER = os.getenv("ELASTICSEARCH_USER", "elastic")
ES_PASS = os.getenv("ELASTICSEARCH_PASSWORD")

client = AsyncElasticsearch(
    hosts=[ES_HOST],
    basic_auth=(ES_USER, ES_PASS),
    verify_certs=False,  # self-signed cert, za dev v redu
)
