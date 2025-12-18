import os
from elasticsearch import AsyncElasticsearch

#for connecting to elasticsearch
ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://elasticsearch:9200")
client = AsyncElasticsearch(hosts=[ES_HOST])