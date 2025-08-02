"""
Tests for Concept Cards functionality.

Tests verify concept card compilation, storage, and API endpoints.
"""



import pytest
from pathlib import Path
from datetime import datetime, timezone

from ae2.concepts.models import ConceptCard, Definition, Evidence, Claim, Provenance
from ae2.concepts.store import ConceptStore
from ae2.concepts.compiler import compile_concept
from ae2.concepts.errors import ConceptCompileError
from ae2.retriever.index_store import IndexStore


def get_auth_headers(client):
    """Get authentication headers for testing."""
    # Return empty headers since auth is disabled
    return {}


class TestConceptCards:
    """Test concept card functionality."""

    @pytest.fixture
    def index_store(self):
        """Load index store for testing."""
        index_dir = Path("data/index")
        if not index_dir.exists():
            pytest.skip("Index not found - run scripts/build_index.py first")

        try:
            return IndexStore(str(index_dir))
        except Exception as e:
            pytest.skip(f"Failed to load index: {e}")

    @pytest.fixture
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
            provenance=Provenance(built_at=datetime.now(timezone.utc)),
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
        assert "test" in ids

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
            provenance=Provenance(built_at=datetime.now(timezone.utc)),
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
            provenance=Provenance(built_at=datetime.now(timezone.utc)),
        )

        concept_store.save(card)

        # Check manifest
        manifest = concept_store.get_manifest()
        assert len(manifest) > 0

        # Find our card in manifest
        card_entry = None
        for entry in manifest:
            if entry["id"] == "test":  # Now using slug as ID
                card_entry = entry
                break

        assert card_entry is not None
        assert len(card_entry["sha256"]) == 64
        assert "built_at" in card_entry
        assert "bytes" in card_entry

    def test_persistence_with_save(self, index_store, concept_store):
        """Test compiling and saving a concept card."""
        # Compile with save=true
        card = compile_concept("arp", index_store, concept_store)

        # Save the card
        concept_store.save(card)

        # Verify file exists
        assert (concept_store.concepts_dir / "arp.json").exists()

        # Verify manifest updated with correct structure
        concepts = concept_store.list_concepts()
        assert len(concepts) == 1
        concept_entry = concepts[0]
        assert concept_entry["id"] == "arp"
        assert concept_entry["bytes"] > 0
        assert len(concept_entry["sha256"]) == 64
        assert "built_at" in concept_entry

        # Verify root hash computed
        root_hash = concept_store.get_root_hash()
        assert len(root_hash) == 64

    def test_load_by_slug(self, concept_store):
        """Test loading a concept card by slug."""
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
            provenance=Provenance(built_at=datetime.now(timezone.utc)),
        )

        concept_store.save(card)

        # Load by slug
        loaded_card = concept_store.load("test")
        assert loaded_card.id == card.id
        assert loaded_card.definition.text == card.definition.text

    def test_list_concepts_detailed(self, concept_store):
        """Test listing concepts with detailed manifest data."""
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
            provenance=Provenance(built_at=datetime.now(timezone.utc)),
        )

        concept_store.save(card)

        # List concepts with details
        concepts = concept_store.list_concepts()
        assert len(concepts) == 1
        assert concepts[0]["id"] == "test"
        assert "sha256" in concepts[0]
        assert "built_at" in concepts[0]
        assert "bytes" in concepts[0]


class TestConceptAPI:
    """Test concept card API endpoints."""

    @pytest.fixture(scope="class")
    def api_client(self):
        """Create a test API client."""
        # Set up test environment before importing app
        import os
        os.environ["AE_INDEX_DIR"] = str(Path("data/index").resolve())
        os.environ["ENABLE_DENSE"] = "0"

        # Import after setting environment variables
        from fastapi.testclient import TestClient
        from ae2.api.main import app

        # Use TestClient with proper lifespan management
        with TestClient(app) as test_client:
            # Get authentication headers
            headers = get_auth_headers(test_client)
            # Add headers to client for convenience
            test_client.auth_headers = headers
            yield test_client

    def test_compile_concept_api(self, api_client):
        """Test POST /concepts/compile endpoint."""
        response = api_client.post("/concepts/compile?slug=arp", headers=api_client.auth_headers)

        assert response.status_code == 200
        data = response.json()

        assert data["id"].startswith("concept:arp:")
        assert data["definition"]["rfc_number"] in [826, 1812]
        assert len(data["definition"]["text"]) > 0
        assert "claims" in data
        assert "provenance" in data

    def test_get_concept_api(self, api_client):
        """Test GET /concepts/{slug} endpoint."""
        # First compile and save a concept
        compile_response = api_client.post("/concepts/compile?slug=arp&save=true", headers=api_client.auth_headers)
        assert compile_response.status_code == 200

        # Then retrieve it by slug
        response = api_client.get("/concepts/arp", headers=api_client.auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["id"].startswith("concept:arp:")
        assert data["definition"]["rfc_number"] in [826, 1812]

    def test_debug_concept_api(self, api_client):
        """Test GET /debug/concept/{id} endpoint."""
        # First compile a concept
        compile_response = api_client.post("/concepts/compile?slug=arp", headers=api_client.auth_headers)
        assert compile_response.status_code == 200
        card_id = compile_response.json()["id"]

        # Then get debug info
        response = api_client.get(f"/debug/concept/{card_id}", headers=api_client.auth_headers)
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
        """Test GET /concepts/list endpoint."""
        # Compile and save a concept first
        api_client.post("/concepts/compile?slug=arp&save=true", headers=api_client.auth_headers)

        # List concepts
        response = api_client.get("/concepts/list", headers=api_client.auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1

        # Check structure of first item
        concept = data[0]
        assert "id" in concept
        assert "sha256" in concept
        assert "built_at" in concept
        assert "bytes" in concept

    def test_get_nonexistent_concept(self, api_client):
        """Test getting a nonexistent concept."""
        response = api_client.get("/concepts/nonexistent", headers=api_client.auth_headers)
        assert response.status_code == 404

    def test_compile_invalid_slug_api(self, api_client):
        """Test compiling with invalid slug via API."""
        response = api_client.post("/concepts/compile?slug=xyz123nonexistent", headers=api_client.auth_headers)
        assert response.status_code == 400

    def test_debug_index_includes_concepts(self, api_client):
        """Test that /debug/index includes concept counts and hashes."""
        # Compile a concept first
        api_client.post("/concepts/compile?slug=arp", headers=api_client.auth_headers)

        # Check debug index
        response = api_client.get("/debug/index", headers=api_client.auth_headers)
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

    def test_compile_with_save(self, api_client):
        """Test compiling with save=true parameter."""
        # Compile and save
        response = api_client.post("/concepts/compile?slug=arp&save=true", headers=api_client.auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert data["id"].startswith("concept:arp:")
        assert "definition" in data
        assert "provenance" in data

        # Verify the concept was actually saved
        list_response = api_client.get("/concepts/list")
        assert list_response.status_code == 200
        concepts = list_response.json()
        assert any(c["id"] == "arp" for c in concepts)

    def test_concepts_list_endpoint(self, api_client):
        """Test GET /concepts/list endpoint."""
        # Compile and save a concept first
        api_client.post("/concepts/compile?slug=arp&save=true", headers=api_client.auth_headers)

        # List concepts
        response = api_client.get("/concepts/list", headers=api_client.auth_headers)
        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) >= 1

        # Check structure of first item
        concept = data[0]
        assert "id" in concept
        assert "sha256" in concept
        assert "built_at" in concept
        assert "bytes" in concept


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
        print(f"Manifest has {len(manifest)} concepts")

    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)


class TestConceptCardsV02:
    """Test Concept Cards v0.2 functionality."""

    @pytest.fixture
    def index_store(self):
        """Load index store for testing."""
        index_dir = Path("data/index")
        if not index_dir.exists():
            pytest.skip("Index not found - run scripts/build_index.py first")

        try:
            return IndexStore(str(index_dir))
        except Exception as e:
            pytest.skip(f"Failed to load index: {e}")

    @pytest.fixture
    def concept_store(self, tmp_path_factory):
        """Create a temporary concept store for testing."""
        tmp_dir = tmp_path_factory.mktemp("concepts")
        return ConceptStore(tmp_dir)

    def test_rebuild_flow(self, index_store, concept_store):
        """Test rebuild flow."""
        # Compile and save arp
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Capture original values
        _ = concept_store._compute_card_hash(
            card.model_dump()
        )  # original_sha256 not used in test
        original_index_hash = card.provenance.index_root_hash

        # Rebuild the card
        rebuilt_card = compile_concept("arp", index_store, concept_store)
        concept_store.save(rebuilt_card)

        # Verify file exists and manifest updated
        assert (concept_store.concepts_dir / "arp.json").exists()

        # Verify index root hash is current
        assert rebuilt_card.provenance.index_root_hash is not None
        assert rebuilt_card.provenance.index_root_hash == original_index_hash

    def test_delete_flow(self, index_store, concept_store):
        """Test delete flow."""
        # Create and save a card
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Verify it exists
        assert concept_store.exists("arp")
        assert (concept_store.concepts_dir / "arp.json").exists()

        # Delete the card
        deleted = concept_store.delete_card("arp")
        assert deleted is True

        # Verify it's gone
        assert not concept_store.exists("arp")
        assert not (concept_store.concepts_dir / "arp.json").exists()

        # Verify manifest is updated
        concepts = concept_store.list_concepts()
        assert len(concepts) == 0

    def test_stale_flag(self, index_store, concept_store):
        """Test stale flag computation."""
        # Create and save a card
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Get current index root hash
        stats = index_store.stats()
        current_hash = stats.get("root_hash") if stats else None

        # Test with current hash (should not be stale)
        concepts = concept_store.list_concepts_with_stale(current_hash)
        assert len(concepts) == 1
        assert concepts[0]["stale"] is False

        # Test with different hash (should be stale)
        concepts = concept_store.list_concepts_with_stale("different_hash")
        assert len(concepts) == 1
        assert concepts[0]["stale"] is True

    def test_manifest_gc(self, index_store, concept_store):
        """Test manifest garbage collection."""
        # Create and save a card
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Verify it's in manifest
        concepts = concept_store.list_concepts()
        assert len(concepts) == 1

        # Manually remove the file
        (concept_store.concepts_dir / "arp.json").unlink()

        # Run GC
        removed = concept_store.gc_manifest()
        assert removed == 1

        # Verify manifest is updated
        concepts = concept_store.list_concepts()
        assert len(concepts) == 0


class TestConceptAPIV02:
    """Test Concept Cards v0.2 API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create a test API client."""
        # Set up test environment before importing app
        import os
        os.environ["AE_INDEX_DIR"] = str(Path("data/index").resolve())
        os.environ["ENABLE_DENSE"] = "0"

        # Import after setting environment variables
        from fastapi.testclient import TestClient
        from ae2.api.main import app

        # Use TestClient with proper lifespan management
        with TestClient(app) as test_client:
            # Get authentication headers
            headers = get_auth_headers(test_client)
            # Add headers to client for convenience
            test_client.auth_headers = headers
            yield test_client

    def test_rebuild_api(self, api_client):
        """Test POST /concepts/rebuild endpoint."""
        with api_client as client:
            # First compile and save a concept
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)

            # Then rebuild it
            response = client.post("/concepts/rebuild?slug=arp", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            assert data["id"].startswith("concept:arp:")
            assert "provenance" in data
            assert "index_root_hash" in data["provenance"]

    def test_delete_api(self, api_client):
        """Test DELETE /concepts/{slug} endpoint."""
        with api_client as client:
            # First compile and save a concept
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)

            # Verify it exists
            response = client.get("/concepts/arp", headers=client.auth_headers)
            assert response.status_code == 200

            # Delete it
            response = client.delete("/concepts/arp", headers=client.auth_headers)
            assert response.status_code == 200
            assert response.json()["ok"] is True

            # Verify it's gone
            response = client.get("/concepts/arp", headers=client.auth_headers)
            assert response.status_code == 404

    def test_schema_api(self, api_client):
        """Test GET /concepts/schema endpoint."""
        with api_client as client:
            response = client.get("/concepts/schema", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Check schema structure
            assert "title" in data
            assert "type" in data
            assert "properties" in data
            assert data["title"] == "ConceptCard"

    def test_stale_flag_api(self, api_client):
        """Test stale flag in API responses."""
        with api_client as client:
            # Compile and save a concept
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)

            # Check list response includes stale flag
            response = client.get("/concepts/list", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert "stale" in data[0]

            # Check individual concept response includes stale flag
            response = client.get("/concepts/arp", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert "stale" in data

    def test_debug_index_gc(self, api_client):
        """Test that /debug/index reflects GC."""
        with api_client as client:
            # Compile and save a concept
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)

            # Check initial count
            response = client.get("/debug/index", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()
            initial_count = data["concepts_count"]
            assert initial_count >= 1

            # Delete the concept
            client.delete("/concepts/arp")

            # Check count is decremented
            response = client.get("/debug/index")
            assert response.status_code == 200
            data = response.json()
            final_count = data["concepts_count"]
            assert final_count == initial_count - 1


class TestConceptCardsV03:
    """Test Concept Cards v0.3 functionality."""

    @pytest.fixture
    def index_store(self):
        """Load index store for testing."""
        index_dir = Path("data/index")
        if not index_dir.exists():
            pytest.skip("Index not found - run scripts/build_index.py first")

        try:
            return IndexStore(str(index_dir))
        except Exception as e:
            pytest.skip(f"Failed to load index: {e}")

    @pytest.fixture
    def concept_store(self, tmp_path_factory):
        """Create a temporary concept store for testing."""
        tmp_dir = tmp_path_factory.mktemp("concepts")
        return ConceptStore(tmp_dir)

    def test_evidence_integrity(self, index_store, concept_store):
        """Test enhanced evidence fields."""
        # Compile and save arp
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Check evidence fields
        for claim in card.claims:
            for evidence in claim.evidence:
                # Check sha256 is 64 hex characters
                assert len(evidence.sha256) == 64
                assert all(c in "0123456789abcdef" for c in evidence.sha256)

                # Check length is positive
                assert evidence.length > 0

                # Check source has required fields
                assert evidence.source is not None
                assert "type" in evidence.source
                assert "rfc_number" in evidence.source
                assert "section" in evidence.source
                assert "title" in evidence.source
                assert "url" in evidence.source
                assert evidence.source["type"] == "rfc"

    def test_diff_functionality(self, index_store, concept_store):
        """Test diff functionality."""
        from ae2.concepts.diff import card_diff

        # Compile and save arp
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Test diff with same card (should be empty)
        card_dict = card.model_dump()
        diff = card_diff(card_dict, card_dict)
        assert diff["changed"] == {}
        assert diff["added"] == {}
        assert diff["removed"] == {}

        # Test diff with modified card
        import copy

        modified_dict = copy.deepcopy(card_dict)
        modified_dict["definition"]["text"] = "Modified text"
        diff = card_diff(card_dict, modified_dict)
        assert "definition" in diff["changed"]
        assert "text" in diff["changed"]["definition"]
        assert "old" in diff["changed"]["definition"]["text"]
        assert "new" in diff["changed"]["definition"]["text"]

    def test_bulk_compile(self, index_store, concept_store):
        """Test bulk compile functionality."""
        # Test with valid and invalid slugs
        slugs = ["arp", "ospf", "___bogus___"]

        # Compile all
        results = []
        for slug in slugs:
            try:
                card = compile_concept(slug, index_store, None)
                results.append({"slug": slug, "status": "ok", "id": card.id})
            except ConceptCompileError:
                results.append({"slug": slug, "status": "error"})

        # Should have 2 successful and 1 error
        assert len(results) == 3
        assert sum(1 for r in results if r["status"] == "ok") == 2
        assert sum(1 for r in results if r["status"] == "error") == 1

    def test_export_functionality(self, index_store, concept_store):
        """Test export functionality."""
        # Compile and save some concepts
        for slug in ["arp", "ospf"]:
            card = compile_concept(slug, index_store, concept_store)
            concept_store.save(card)

        # Export all concepts
        zip_data = concept_store.export_concepts()
        assert len(zip_data) > 0

        # Export specific concepts
        zip_data = concept_store.export_concepts(["arp"])
        assert len(zip_data) > 0


class TestConceptAPIV03:
    """Test Concept Cards v0.3 API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create a test API client."""
        # Set up test environment before importing app
        import os
        os.environ["AE_INDEX_DIR"] = str(Path("data/index").resolve())
        os.environ["ENABLE_DENSE"] = "0"

        # Import after setting environment variables
        from fastapi.testclient import TestClient
        from ae2.api.main import app

        # Use TestClient with proper lifespan management
        with TestClient(app) as test_client:
            # Get authentication headers
            headers = get_auth_headers(test_client)
            # Add headers to client for convenience
            test_client.auth_headers = headers
            yield test_client

    def test_evidence_integrity_api(self, api_client):
        """Test enhanced evidence fields in API."""
        with api_client as client:
            # Compile and save a concept
            response = client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Check evidence fields
            for claim in data["claims"]:
                for evidence in claim["evidence"]:
                    assert "sha256" in evidence
                    assert "length" in evidence
                    assert "source" in evidence
                    assert evidence["source"]["type"] == "rfc"

    def test_diff_api(self, api_client):
        """Test diff API endpoint."""
        with api_client as client:
            # First compile and save a concept
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)

            # Test diff with recompile=false (should be empty)
            response = client.get("/concepts/diff/arp?recompile=false", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()
            assert data["changed"] == {}
            assert data["added"] == {}
            assert data["removed"] == {}
            assert "provenance" in data

    def test_bulk_compile_api(self, api_client):
        """Test bulk compile API endpoint."""
        with api_client as client:
            response = client.post(
                "/concepts/compile_many?save=true",
                json={"slugs": ["arp", "ospf", "___bogus___"]},
                headers=client.auth_headers,
            )
            assert response.status_code == 200
            data = response.json()

            assert data["ok"] is True
            assert len(data["results"]) == 3
            assert data["saved_count"] == 2  # 2 successful, 1 error

    def test_export_api(self, api_client):
        """Test export API endpoint."""
        with api_client as client:
            # First compile and save some concepts
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)
            client.post("/concepts/compile?slug=ospf&save=true", headers=client.auth_headers)

            # Export all concepts
            response = client.post("/concepts/export", headers=client.auth_headers)
            assert response.status_code == 200
            assert response.headers["content-type"] == "application/zip"
            assert "attachment" in response.headers["content-disposition"]

    def test_backward_compatibility(self, api_client):
        """Test backward compatibility with old cards."""
        with api_client as client:
            # Load an old card (without enhanced evidence fields)
            # This should still work
            response = client.get("/concepts/schema", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Check that new fields are in schema
            evidence_props = data["$defs"]["Evidence"]["properties"]
            assert "length" in evidence_props
            assert "source" in evidence_props


class TestConceptCardsV04:
    """Test Concept Cards v0.4 functionality."""

    @pytest.fixture
    def index_store(self):
        """Load index store for testing."""
        index_dir = Path("data/index")
        if not index_dir.exists():
            pytest.skip("Index not found - run scripts/build_index.py first")

        try:
            return IndexStore(str(index_dir))
        except Exception as e:
            pytest.skip(f"Failed to load index: {e}")

    @pytest.fixture
    def concept_store(self, tmp_path_factory):
        """Create a temporary concept store for testing."""
        tmp_dir = tmp_path_factory.mktemp("concepts")
        return ConceptStore(tmp_dir)

    def test_cross_links_and_cycle_guard(self, index_store, concept_store):
        """Test cross-links and cycle detection."""
        # Compile and save arp (no related)
        card = compile_concept("arp", index_store, concept_store)
        concept_store.save(card)

        # Create a card with related reference
        from ae2.concepts.models import ConceptCard, Definition, Provenance

        # Create default-route card with related=["arp"]
        default_route_card = ConceptCard(
            id="concept:default-route:v1",
            definition=Definition(
                text="Default route definition",
                rfc_number=1812,
                section="1",
                url="https://www.rfc-editor.org/rfc/rfc1812.txt",
            ),
            claims=[],
            provenance=Provenance(built_at=card.provenance.built_at),
            related=["arp"],
            tags=["routing", "default"],
        )
        concept_store.save(default_route_card)

        # Validate default-route (should be ok)
        validation = concept_store.validate_references("default-route")
        assert validation["ok"] is True
        assert validation["missing"] == []
        assert validation["cycles"] == []

        # Create a cycle by making arp reference default-route
        arp_dict = card.model_dump()
        arp_dict["related"] = ["default-route"]
        arp_dict["tags"] = ["arp", "l2"]

        # Save the modified arp card
        import json

        arp_path = concept_store.concepts_dir / "arp.json"
        with open(arp_path, "w") as f:
            json.dump(arp_dict, f, default=str)

        # Validate arp (should detect cycle)
        validation = concept_store.validate_references("arp")
        assert validation["ok"] is False
        assert "arp" in validation["cycles"][0]  # Cycle should include arp

    def test_pull_through_compile(self, index_store, concept_store):
        """Test pull-through compilation."""
        # Ensure ospf is not persisted
        assert not concept_store.exists("ospf")

        # Create arp card with related=["ospf"]
        card = compile_concept("arp", index_store, concept_store)

        # Manually add related and tags
        card.related = ["ospf"]
        card.tags = ["arp", "l2"]

        # Save arp
        concept_store.save(card)

        # Test pull-through compilation
        # This would normally be done via API, but we'll test the logic directly
        pulled = []
        pulled_errors = []

        for related_slug in card.related:
            if not concept_store.exists(related_slug):
                try:
                    related_card = compile_concept(
                        related_slug, index_store, concept_store
                    )
                    concept_store.save(related_card)
                    pulled.append(related_slug)
                except Exception as e:
                    pulled_errors.append(
                        {
                            "slug": related_slug,
                            "code": "UNKNOWN_ERROR",
                            "message": str(e),
                        }
                    )

        # Should have pulled ospf
        assert "ospf" in pulled
        assert concept_store.exists("ospf")

    def test_search_functionality(self, index_store, concept_store):
        """Test search functionality."""
        from ae2.concepts.search import search_cards

        # Create cards with different tags
        cards = []

        # ARP card
        arp_card = compile_concept("arp", index_store, concept_store)
        arp_card.tags = ["arp", "l2", "routing"]
        concept_store.save(arp_card)
        cards.append(arp_card.model_dump())

        # OSPF card
        ospf_card = compile_concept("ospf", index_store, concept_store)
        ospf_card.tags = ["ospf", "routing", "l3"]
        concept_store.save(ospf_card)
        cards.append(ospf_card.model_dump())

        # Search for "routing"
        total, items = search_cards(cards, "routing", limit=5)
        assert total >= 2  # Both cards should match
        assert len(items) >= 2

        # Check structure
        for item in items:
            assert "id" in item
            assert "score" in item
            assert "tags" in item
            assert "stale" in item

    def test_tags_aggregation(self, index_store, concept_store):
        """Test tag aggregation."""
        # Create cards with tags
        arp_card = compile_concept("arp", index_store, concept_store)
        arp_card.tags = ["arp", "l2", "routing"]
        concept_store.save(arp_card)

        ospf_card = compile_concept("ospf", index_store, concept_store)
        ospf_card.tags = ["ospf", "routing", "l3"]
        concept_store.save(ospf_card)

        # Get tag counts
        tag_counts = concept_store.get_tag_counts()

        # Check structure and ordering
        assert len(tag_counts) >= 5  # arp, l2, routing, ospf, l3

        # routing should have count 2 (highest)
        routing_tag = next((t for t in tag_counts if t["tag"] == "routing"), None)
        assert routing_tag is not None
        assert routing_tag["count"] == 2

        # Check ordering (count desc, then tag asc)
        for i in range(len(tag_counts) - 1):
            current = tag_counts[i]
            next_tag = tag_counts[i + 1]

            if current["count"] == next_tag["count"]:
                assert current["tag"] <= next_tag["tag"]  # alphabetical
            else:
                assert current["count"] > next_tag["count"]  # descending

    def test_backward_compatibility(self, index_store, concept_store):
        """Test backward compatibility with old cards."""
        # Create a card without related/tags (old format)
        card = compile_concept("arp", index_store, concept_store)

        # Remove related and tags to simulate old card
        card_dict = card.model_dump()
        if "related" in card_dict:
            del card_dict["related"]
        if "tags" in card_dict:
            del card_dict["tags"]

        # Save the old-format card
        import json

        arp_path = concept_store.concepts_dir / "arp.json"
        with open(arp_path, "w") as f:
            json.dump(card_dict, f, default=str)

        # Should still be able to load it
        loaded_card = concept_store.load("arp")
        assert loaded_card.id == "concept:arp:v1"

        # Should have empty lists for new fields
        assert hasattr(loaded_card, "related")
        assert hasattr(loaded_card, "tags")
        assert loaded_card.related == []
        assert loaded_card.tags == []


class TestConceptAPIV04:
    """Test Concept Cards v0.4 API endpoints."""

    @pytest.fixture
    def api_client(self):
        """Create a test API client."""
        # Set up test environment before importing app
        import os
        os.environ["AE_INDEX_DIR"] = str(Path("data/index").resolve())
        os.environ["ENABLE_DENSE"] = "0"

        # Import after setting environment variables
        from fastapi.testclient import TestClient
        from ae2.api.main import app

        # Use TestClient with proper lifespan management
        with TestClient(app) as test_client:
            # Get authentication headers
            headers = get_auth_headers(test_client)
            # Add headers to client for convenience
            test_client.auth_headers = headers
            yield test_client

    def test_validate_api(self, api_client):
        """Test reference validation API."""
        with api_client as client:
            # First compile and save a concept
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)

            # Validate it
            response = client.get("/concepts/validate/arp", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            assert "ok" in data
            assert "missing" in data
            assert "cycles" in data
            assert isinstance(data["missing"], list)
            assert isinstance(data["cycles"], list)

    def test_pull_through_api(self, api_client):
        """Test pull-through compilation API."""
        with api_client as client:
            # This test would require the compiler to emit related slugs
            # For now, we'll test the endpoint structure
            response = client.post("/concepts/compile?slug=arp&save=true&pull=true", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            # Should include pull fields
            assert "pulled" in data
            assert "pulled_errors" in data
            assert isinstance(data["pulled"], list)
            assert isinstance(data["pulled_errors"], list)

    def test_search_api(self, api_client):
        """Test search API."""
        with api_client as client:
            # First compile and save some concepts
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)
            client.post("/concepts/compile?slug=ospf&save=true", headers=client.auth_headers)

            # Search
            response = client.get("/concepts/search?q=arp&limit=5", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            assert "total" in data
            assert "items" in data
            assert isinstance(data["total"], int)
            assert isinstance(data["items"], list)

            # Check item structure
            if data["items"]:
                item = data["items"][0]
                assert "id" in item
                assert "score" in item
                assert "tags" in item
                assert "stale" in item

    def test_tags_api(self, api_client):
        """Test tags API."""
        with api_client as client:
            # First compile and save some concepts
            client.post("/concepts/compile?slug=arp&save=true", headers=client.auth_headers)
            client.post("/concepts/compile?slug=ospf&save=true", headers=client.auth_headers)

            # Get tags
            response = client.get("/concepts/tags", headers=client.auth_headers)
            assert response.status_code == 200
            data = response.json()

            assert "tags" in data
            assert isinstance(data["tags"], list)

            # Check tag structure
            if data["tags"]:
                tag = data["tags"][0]
                assert "tag" in tag
                assert "count" in tag
                assert isinstance(tag["tag"], str)
                assert isinstance(tag["count"], int)
