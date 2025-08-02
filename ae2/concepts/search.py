"""
Concept Card search functionality.

This module provides lightweight in-memory search over persisted concept cards.
"""

import re
from typing import List, Dict, Tuple
from collections import Counter, defaultdict
import math


class ConceptSearch:
    """Lightweight search over persisted concept cards."""

    def __init__(self):
        self.cards = {}  # slug -> card_dict
        self.token_index = defaultdict(list)  # token -> [(slug, count), ...]
        self.document_lengths = {}  # slug -> token_count

    def index_cards(self, cards: List[Dict]):
        """Build search index from list of card dictionaries."""
        self.cards = {card["id"]: card for card in cards}
        self.token_index.clear()
        self.document_lengths.clear()

        # Build token index
        for slug, card in self.cards.items():
            # Create searchable text
            text_parts = [
                slug,  # id
                " ".join(card.get("tags", [])),  # tags
                card.get("definition", {}).get("text", ""),  # definition text
            ]
            text = " ".join(text_parts).lower()

            # Tokenize
            tokens = self._tokenize(text)
            token_counts = Counter(tokens)

            # Store document length
            self.document_lengths[slug] = len(tokens)

            # Add to inverted index
            for token, count in token_counts.items():
                self.token_index[token].append((slug, count))

    def search_cards(
        self, query: str, limit: int = 10, offset: int = 0, stale_resolver=None
    ) -> Tuple[int, List[Dict]]:
        """Search cards with deterministic scoring.

        Args:
            query: Search query string
            limit: Maximum number of results
            offset: Number of results to skip
            stale_resolver: Function to resolve stale flag (slug -> bool)

        Returns:
            Tuple of (total_count, list_of_results)
        """
        if not query.strip():
            return 0, []

        # Tokenize query
        query_tokens = self._tokenize(query.lower())
        if not query_tokens:
            return 0, []

        # Calculate scores using TF-IDF
        scores = {}
        for slug in self.cards:
            score = self._calculate_score(slug, query_tokens)
            if score > 0:
                scores[slug] = score

        # Sort by score (descending), then by slug (ascending) for ties
        sorted_results = sorted(scores.items(), key=lambda x: (-x[1], x[0]))

        # Apply pagination
        total = len(sorted_results)
        paginated_results = sorted_results[offset : offset + limit]

        # Build response items
        items = []
        for slug, score in paginated_results:
            card = self.cards[slug]
            item = {
                "id": slug,
                "score": round(score, 4),
                "tags": sorted(card.get("tags", [])),  # Deterministic sorting
                "stale": stale_resolver(slug) if stale_resolver else False,
            }
            items.append(item)

        return total, items

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into searchable tokens."""
        # Split on non-alphanumeric characters
        tokens = re.findall(r"\b[a-z0-9]+\b", text.lower())
        # Remove empty tokens
        return [token for token in tokens if token]

    def _calculate_score(self, slug: str, query_tokens: List[str]) -> float:
        """Calculate TF-IDF score for a document against query tokens."""
        if slug not in self.cards:
            return 0.0

        score = 0.0
        doc_tokens = self._get_document_tokens(slug)

        for query_token in query_tokens:
            # Calculate TF-IDF for this token
            tf = doc_tokens.get(query_token, 0) / max(len(doc_tokens), 1)
            idf = self._calculate_idf(query_token)
            score += tf * idf

        return score

    def _get_document_tokens(self, slug: str) -> Dict[str, int]:
        """Get token counts for a document."""
        card = self.cards.get(slug, {})
        text_parts = [
            slug,
            " ".join(card.get("tags", [])),
            card.get("definition", {}).get("text", ""),
        ]
        text = " ".join(text_parts).lower()
        tokens = self._tokenize(text)
        return Counter(tokens)

    def _calculate_idf(self, token: str) -> float:
        """Calculate inverse document frequency for a token."""
        doc_count = len(self.token_index.get(token, []))
        if doc_count == 0:
            return 0.0

        total_docs = len(self.cards)
        # Use a minimum IDF value to avoid log(1) = 0
        if doc_count == total_docs:
            return 0.1  # Small positive value for tokens that appear in all documents
        else:
            return math.log(total_docs / doc_count)


def search_cards(
    cards: List[Dict], query: str, limit: int = 10, offset: int = 0, stale_resolver=None
) -> Tuple[int, List[Dict]]:
    """Convenience function to search cards.

    Args:
        cards: List of card dictionaries
        query: Search query
        limit: Maximum results
        offset: Results offset
        stale_resolver: Function to resolve stale flag

    Returns:
        Tuple of (total_count, results)
    """
    searcher = ConceptSearch()
    searcher.index_cards(cards)
    return searcher.search_cards(query, limit, offset, stale_resolver)
