import os
import pytest
from ae2.api.main import app
from fastapi.testclient import TestClient
from ae2.retriever.index_store import IndexStore
from ae2.concepts.store import ConceptStore
import ae2.api.main as api_main


@pytest.fixture(scope="session")
def client():
    os.environ["AE_DISABLE_AUTH"] = "true"
    os.environ["AE_JSON_LOGS"] = "0"
    api_main.store = IndexStore("data/index")
    api_main.concept_store = ConceptStore()
    return TestClient(app)
