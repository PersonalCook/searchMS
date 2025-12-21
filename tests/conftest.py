import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_ROOT_DIR = Path(__file__).resolve().parents[1]
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("SOCIAL_SERVICE_URL", "http://social-service.local")
os.environ.setdefault("USER_SERVICE_URL", "http://user-service.local")
os.environ.setdefault("RECIPE_SERVICE_URL", "http://recipe-service.local/recipes")
os.environ.setdefault("ELASTICSEARCH_HOST", "http://localhost:9200")
os.environ.setdefault("ELASTICSEARCH_PASSWORD", "test-secret")

from app.main import app  # noqa: E402

app.router.on_startup.clear()


@pytest.fixture()
def client():
    app.dependency_overrides = {}
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides = {}
