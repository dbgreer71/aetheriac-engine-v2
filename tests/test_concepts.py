"""
Tests for Concept Cards functionality.

Tests verify concept card compilation, storage, and API endpoints.
"""

import pytest
from pathlib import Path
from datetime import datetime

from ae2.concepts.models import ConceptCard, Definition, Evidence, Claim, Provenance
from ae2.concepts.store import ConceptStore
from ae2.concepts.compiler import compile_concept
from ae2.concepts.errors import ConceptCompileError
from ae2.retriever.index_store import IndexStore


class TestConceptCards:
    """Test concept card functionality."""

    @pytest.fixture(scope="class")
    def index_store(self):
        """Load index store for testing."""
        index_dir = Path("data/index")
        if not index_dir.exists():
            pytest.skip("Index not found - run scripts/build_index.py first")

        try:
            return IndexStore(str(index_dir))
        except Exception as e:
            pytest.skip(f"Failed to load index: {e}")

    @pytest.fixture(scope="class")
    def concept_store(self, tmp_path_factory):
        """Create a temporary concept store for testing."""
        tmp_dir = tmp_path_factory.mktemp("concepts")
        return ConceptStore(tmp_dir)

    def test_compile_arp_concept(self, index_store, concept_store):
        """Test compiling ARP concept card."""
        card = compile_concept("arp", index_store, concept_store)

        # Verify card structure
        assert card.id.startswith("concept:arp:")
        assert card.definition.rfc_number in [
            826,
            1812,
        ]  # RFC 826 (ARP) or RFC 1812 (IP routing)
        assert isinstance(card.definition.text, str)
        assert len(card.definition.text) > 0
        assert card.definition.url.startswith("https://www.rfc-editor.org/rfc/rfc")

        # Verify claims
        assert isinstance(card.claims, list)
        for claim in card.claims:
            assert isinstance(claim.text, str)
            assert len(claim.text) > 0
            assert isinstance(claim.evidence, list)
            for evidence in claim.evidence:
                assert evidence.type == "rfc"
                assert evidence.url_or_path.startswith(
                    "https://www.rfc-editor.org/rfc/rfc"
                )
                assert len(evidence.sha256) == 64  # SHA256 hex length

        # Verify provenance
        assert isinstance(card.provenance.built_at, datetime)

    def test_store_save_load_roundtrip(self, concept_store):
        """Test store save/load roundtrip equality."""
        # Create a test card
        definition = Definition(
            text="Test definition",
            rfc_number=826,
            section="1",
            url="https://www.rfc-editor.org/rfc/rfc826.txt",
        )

        evidence = Evidence(
            type="rfc",
            url_or_path="https://www.rfc-editor.org/rfc/rfc826.txt",
            sha256="a" * 64,
        )

        claim = Claim(text="Test claim", evidence=[evidence])

        card = ConceptCard(
            id="concept:test:v1",
            definition=definition,
            claims=[claim],
            provenance=Provenance(built_at=datetime.utcnow()),
        )

        # Save and reload
        concept_store.save(card)
        loaded_card = concept_store.load(card.id)

        # Compare via dict (handles datetime serialization)
        assert card.model_dump() == loaded_card.model_dump()

    def test_store_list_ids(self, concept_store):
        """Test listing concept card IDs."""
        # Create and save a test card
        definition = Definition(
            text="Test definition",
            rfc_number=826,
            section="1",
            url="https://www.rfc-editor.org/rfc/rfc826.txt",
        )

        card = ConceptCard(
            id="concept:test:v1",
            definition=definition,
            claims=[],
            provenance=Provenance(built_at=datetime.utcnow()),
        )

        concept_store.save(card)

        # List IDs
        ids = concept_store.list_ids()
        assert "concept:test:v1" in ids

    def test_store_exists(self, concept_store):
        """Test checking if concept card exists."""
        # Create and save a test card
        definition = Definition(
            text="Test definition",
            rfc_number=826,
            section="1",
            url="https://www.rfc-editor.org/rfc/rfc826.txt",
        )

        card = ConceptCard(
            id="concept:test:v1",
            definition=definition,
            claims=[],
            provenance=Provenance(built_at=datetime.utcnow()),
        )

        concept_store.save(card)

        # Check existence
        assert concept_store.exists("concept:test:v1")
        assert not concept_store.exists("concept:nonexistent:v1")

    def test_compile_without_store(self, index_store):
        """Test compiling concept without persistence."""
        card = compile_concept("arp", index_store, None)

        assert card.id.startswith("concept:arp:")
        assert card.definition.rfc_number in [826, 1812]
        assert len(card.definition.text) > 0

    def test_compile_invalid_slug(self, index_store):
        """Test compiling with invalid slug."""
        # Use a very specific invalid slug that should return no meaningful results
        with pytest.raises(ConceptCompileError) as e:
            compile_concept("xyz123nonexistent", index_store, None)
        assert e.value.code == "LOW_CONFIDENCE"
        assert "min_score" in str(e.value)

    def test_manifest_management(self, concept_store):
        """Test manifest file management."""
        # Create and save a test card
        definition = Definition(
            text="Test definition",
            rfc_number=826,
            section="1",
            url="https://www.rfc-editor.org/rfc/rfc826.txt",
        )

        card = ConceptCard(
            id="concept:test:v1",
            definition=definition,
            claims=[],
            provenance=Provenance(built_at=datetime.utcnow()),
        )

        concept_store.save(card)

        # Check manifest
        manifest = concept_store.get_manifest()
        assert "concepts" in manifest
        assert len(manifest["concepts"]) > 0

        # Find our card in manifest
        card_entry = None
        for entry in manifest["concepts"]:
            if entry["id"] == "concept:test:v1":
                card_entry = entry
                break

        assert card_entry is not None
        assert card_entry["path"] == "concept:test:v1.json"
        assert len(card_entry["sha256"]) == 64
        assert "built_at" in card_entry


class TestConceptAPI:
    """Test concept card API endpoints."""

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create a test API client."""
        from fastapi.testclient import TestClient
        from ae2.api.main import app

        # Set up test environment
        import os

        os.environ["AE_INDEX_DIR"] = str(Path("data/index").resolve())
        os.environ["ENABLE_DENSE"] = "0"

        return TestClient(app)

    def test_compile_concept_api(self, api_client):
        """Test POST /concepts/compile endpoint."""
        with api_client as client:
            response = client.post("/concepts/compile?slug=arp")

            assert response.status_code == 200
            data = response.json()

            assert data["id"].startswith("concept:arp:")
            assert data["definition"]["rfc_number"] in [826, 1812]
            assert len(data["definition"]["text"]) > 0
            assert "claims" in data
            assert "provenance" in data

    def test_get_concept_api(self, api_client):
        """Test GET /concepts/{id} endpoint."""
        with api_client as client:
            # First compile a concept
            compile_response = client.post("/concepts/compile?slug=arp")
            assert compile_response.status_code == 200
            card_id = compile_response.json()["id"]

            # Then retrieve it
            response = client.get(f"/concepts/{card_id}")
            assert response.status_code == 200
            data = response.json()

            assert data["id"] == card_id
            assert data["definition"]["rfc_number"] in [826, 1812]

    def test_debug_concept_api(self, api_client):
        """Test GET /debug/concept/{id} endpoint."""
        with api_client as client:
            # First compile a concept
            compile_response = client.post("/concepts/compile?slug=arp")
            assert compile_response.status_code == 200
            card_id = compile_response.json()["id"]

            # Then get debug info
            response = client.get(f"/debug/concept/{card_id}")
            assert response.status_code == 200
            data = response.json()

            assert "card" in data
            assert "retrieval_trace" in data
            assert data["card"]["id"] == card_id

            # Check retrieval trace
            trace = data["retrieval_trace"]
            assert "slug" in trace
            assert "target_rfcs" in trace
            assert "top_hits" in trace
            assert len(trace["top_hits"]) > 0

            # Check that top hits have scores
            for hit in trace["top_hits"]:
                assert "scores" in hit
                scores = hit["scores"]
                assert "tfidf" in scores
                assert "bm25" in scores
                assert "hybrid" in scores

    def test_list_concepts_api(self, api_client):
        """Test GET /concepts endpoint."""
        with api_client as client:
            # Compile a concept first
            client.post("/concepts/compile?slug=arp")

            # List concepts
            response = client.get("/concepts")
            assert response.status_code == 200
            data = response.json()

            assert "concept_ids" in data
            assert isinstance(data["concept_ids"], list)
            assert any("concept:arp:" in cid for cid in data["concept_ids"])

    def test_get_nonexistent_concept(self, api_client):
        """Test getting a nonexistent concept."""
        with api_client as client:
            response = client.get("/concepts/concept:nonexistent:v1")
            assert response.status_code == 404

    def test_compile_invalid_slug_api(self, api_client):
        """Test compiling with invalid slug via API."""
        with api_client as client:
            response = client.post("/concepts/compile?slug=xyz123nonexistent")
            assert response.status_code == 400

    def test_debug_index_includes_concepts(self, api_client):
        """Test that /debug/index includes concept counts and hashes."""
        with api_client as client:
            # Compile a concept first
            client.post("/concepts/compile?slug=arp")

            # Check debug index
            response = client.get("/debug/index")
            assert response.status_code == 200
            data = response.json()

            # Verify concept fields are present
            assert "concepts_count" in data
            assert "concepts_root_hash" in data
            assert isinstance(data["concepts_count"], int)
            assert data["concepts_count"] >= 1  # Should have at least the ARP concept

            # If concepts exist, hash should be present
            if data["concepts_count"] > 0:
                assert data["concepts_root_hash"] is not None
                assert len(data["concepts_root_hash"]) == 64  # SHA256 hex length


if __name__ == "__main__":
    # Quick manual test
    index_dir = Path("data/index")
    if not index_dir.exists():
        print("Index not found - run scripts/build_index.py first")
        exit(1)

    try:
        index_store = IndexStore(str(index_dir))
        concept_store = ConceptStore()

        print("Testing ARP concept compilation...")
        card = compile_concept("arp", index_store, concept_store)
        print(f"Compiled card: {card.id}")
        print(f"Definition RFC: {card.definition.rfc_number}")
        print(f"Claims: {len(card.claims)}")

        print("\nTesting store roundtrip...")
        loaded_card = concept_store.load(card.id)
        print(f"Loaded card ID: {loaded_card.id}")

        print("\nTesting manifest...")
        manifest = concept_store.get_manifest()
        print(f"Manifest has {len(manifest['concepts'])} concepts")

    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
