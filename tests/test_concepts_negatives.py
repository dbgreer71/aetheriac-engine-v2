"""
Tests for Concept Cards negative examples and abstention.
"""

import pytest
from fastapi.testclient import TestClient
from ae2.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_concept_negatives_abstain(client):
    """Test that off-topic queries abstain from concept routing."""
    negative_queries = [
        "weather in paris",
        "recipe for chocolate cake",
        "movie reviews",
        "stock market prices",
        "cooking instructions",
        "travel destinations",
        "music recommendations",
        "book reviews",
        "sports scores",
        "restaurant reviews",
    ]

    for query in negative_queries:
        response = client.post("/query?mode=auto", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "ABSTAIN"
        assert data.get("reason_code") in ["OFFTOPIC", "LOW_CONFIDENCE"]


def test_concept_negatives_confidence_threshold(client):
    """Test that ambiguous queries abstain due to low confidence."""
    ambiguous_queries = [
        "protocol",
        "network",
        "address",
        "connection",
        "data",
        "packet",
        "routing",
        "switching",
        "protocols",
        "networks",
    ]

    for query in ambiguous_queries:
        response = client.post("/query?mode=auto", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        # Should either abstain or have low confidence
        assert data["intent"] in ["ABSTAIN", "DEFINE"]
        if data["intent"] == "ABSTAIN":
            assert data.get("reason_code") in ["LOW_CONFIDENCE", "AMBIGUOUS"]


def test_concept_negatives_short_queries(client):
    """Test that very short queries abstain."""
    short_queries = ["ip", "arp", "tcp", "bgp", "ospf", "a", "b", "c", "x", "y"]

    for query in short_queries:
        response = client.post("/query?mode=auto", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "ABSTAIN"
        assert data.get("reason_code") in ["SHORT_QUERY", "LOW_CONFIDENCE"]


def test_concept_negatives_no_network_context(client):
    """Test that queries without network context abstain."""
    non_network_queries = [
        "how to cook pasta",
        "best restaurants in town",
        "movie showtimes",
        "weather forecast",
        "shopping deals",
        "fitness tips",
        "gardening advice",
        "pet care",
        "home improvement",
        "car maintenance",
    ]

    for query in non_network_queries:
        response = client.post("/query?mode=auto", json={"query": query})
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "ABSTAIN"
        assert data.get("reason_code") == "OFFTOPIC"


def test_concept_negatives_debug_route(client):
    """Test debug route shows correct abstention reasons for negatives."""
    test_cases = [
        ("weather in paris", "OFFTOPIC"),
        ("recipe for cake", "OFFTOPIC"),
        ("protocol", "LOW_CONFIDENCE"),
        ("ip", "SHORT_QUERY"),
    ]

    for query, expected_reason in test_cases:
        response = client.get(f"/debug/route?query={query}")
        assert response.status_code == 200

        data = response.json()
        assert data["intent"] == "ABSTAIN"
        assert data.get("reason_code") == expected_reason


def test_concept_negatives_consistency(client):
    """Test that negative queries consistently abstain across multiple runs."""
    negative_query = "weather in paris"

    responses = []
    for _ in range(3):
        response = client.post("/query?mode=auto", json={"query": negative_query})
        assert response.status_code == 200
        responses.append(response.json())

    # All responses should be consistent
    first_response = responses[0]
    for response in responses[1:]:
        assert response["intent"] == first_response["intent"]
        assert response.get("reason_code") == first_response.get("reason_code")
