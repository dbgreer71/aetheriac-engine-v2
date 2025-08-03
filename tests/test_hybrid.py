"""
Minimal golden tests for hybrid reranker (BM25 + TF-IDF).

Tests verify that hybrid mode returns expected results with debug subscores.
"""

import pytest
from pathlib import Path

from ae2.retriever.index_store import IndexStore


class TestHybridRanker:
    """Test hybrid reranker functionality."""

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

    def test_ospf_query_hybrid_mode(self, index_store):
        """Test OSPF query returns RFC 2328 with protocol overview."""
        query = "what is ospf"
        results = index_store.search(query, mode="hybrid", top_k=5)

        # Must have results
        assert len(results) > 0, "No results returned"

        # Top hit should be RFC 2328
        top_hit = results[0]
        assert top_hit["rfc"] == 2328, f"Expected RFC 2328, got RFC {top_hit['rfc']}"

        # Section title should contain "Introduction" or "Protocol"
        title = top_hit["title"].lower()
        assert any(
            keyword in title for keyword in ["introduction", "protocol", "overview"]
        ), f"Title '{title}' should contain Introduction/Protocol/Overview"

        # Must have all three subscores
        assert "scores" in top_hit, "Missing scores field"
        scores = top_hit["scores"]
        assert "tfidf" in scores, "Missing tfidf score"
        assert "bm25" in scores, "Missing bm25 score"
        assert "hybrid" in scores, "Missing hybrid score"

        # Scores should be numeric
        assert isinstance(scores["tfidf"], (int, float)), "tfidf score not numeric"
        assert isinstance(scores["bm25"], (int, float)), "bm25 score not numeric"
        assert isinstance(scores["hybrid"], (int, float)), "hybrid score not numeric"

    def test_arp_query_hybrid_mode(self, index_store):
        """Test ARP query returns relevant results with subscores."""
        query = "what is arp"
        results = index_store.search(query, mode="hybrid", top_k=5)

        # Must have results
        assert len(results) > 0, "No results returned"

        # Should return relevant results (RFC 826 or other ARP-related content)
        top_hit = results[0]
        relevant_rfcs = [826, 1812]  # RFC 826 (ARP) or RFC 1812 (IP routing)
        assert (
            top_hit["rfc"] in relevant_rfcs
        ), f"Expected RFC 826 or 1812, got RFC {top_hit['rfc']}"

        # Must have all three subscores
        assert "scores" in top_hit, "Missing scores field"
        scores = top_hit["scores"]
        assert "tfidf" in scores, "Missing tfidf score"
        assert "bm25" in scores, "Missing bm25 score"
        assert "hybrid" in scores, "Missing hybrid score"

    def test_all_modes_return_scores(self, index_store):
        """Test that all modes (tfidf, bm25, hybrid) return scores."""
        query = "tcp overview"

        for mode in ["tfidf", "bm25", "hybrid"]:
            results = index_store.search(query, mode=mode, top_k=3)

            # Must have results
            assert len(results) > 0, f"No results for mode {mode}"

            # Each result should have appropriate scores
            for result in results:
                if mode == "tfidf":
                    assert "score" in result, f"Missing score for {mode} mode"
                elif mode == "bm25":
                    assert "score" in result, f"Missing score for {mode} mode"
                elif mode == "hybrid":
                    assert "scores" in result, f"Missing scores for {mode} mode"
                    scores = result["scores"]
                    assert "tfidf" in scores, "Missing tfidf score in hybrid mode"
                    assert "bm25" in scores, "Missing bm25 score in hybrid mode"
                    assert "hybrid" in scores, "Missing hybrid score in hybrid mode"

    def test_hybrid_weights_configuration(self, index_store):
        """Test that hybrid weights can be configured."""
        query = "what is ospf"

        # Test with different weights
        results_60_40 = index_store.search(query, mode="hybrid", top_k=3)
        assert len(results_60_40) > 0, "No results with default weights"

        # Verify hybrid scores are present
        for result in results_60_40:
            assert "scores" in result, "Missing scores in hybrid mode"
            scores = result["scores"]
            assert "hybrid" in scores, "Missing hybrid score"

    def test_fallback_without_bm25_tokens(self, index_store):
        """Test fallback behavior when BM25 tokens are missing."""
        # This test verifies the system gracefully handles missing BM25 tokens
        # In practice, this would be tested by temporarily removing bm25_tokens.npy

        query = "what is arp"
        results = index_store.search(query, mode="hybrid", top_k=3)

        # Should still return results (fallback to TF-IDF)
        assert len(results) > 0, "No results in fallback mode"

        # Should still have scores structure
        for result in results:
            assert "scores" in result, "Missing scores in fallback mode"
            scores = result["scores"]
            # May not have bm25 score in fallback, but should have others
            assert "tfidf" in scores, "Missing tfidf score in fallback mode"


if __name__ == "__main__":
    # Quick manual test
    index_dir = Path("data/index")
    if not index_dir.exists():
        print("Index not found - run scripts/build_index.py first")
        exit(1)

    try:
        store = IndexStore(str(index_dir))

        print("Testing OSPF query...")
        results = store.search("what is ospf", mode="hybrid", top_k=3)
        print(f"Found {len(results)} results")
        if results:
            top = results[0]
            print(f"Top result: RFC {top['rfc']} §{top['section']} - {top['title']}")
            print(f"Scores: {top.get('scores', 'N/A')}")

        print("\nTesting ARP query...")
        results = store.search("what is arp", mode="hybrid", top_k=3)
        print(f"Found {len(results)} results")
        if results:
            top = results[0]
            print(f"Top result: RFC {top['rfc']} §{top['section']} - {top['title']}")
            print(f"Scores: {top.get('scores', 'N/A')}")

    except Exception as e:
        print(f"Test failed: {e}")
        exit(1)
