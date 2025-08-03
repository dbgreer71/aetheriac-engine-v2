from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import pickle
import numpy as np
import os
import re
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

# Import cache if available
try:
    from ..common.ttl_lru import cache_get, cache_set

    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False

# Try to import BM25, fallback gracefully
try:
    from rank_bm25 import BM25Okapi

    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False


class IndexStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.sections: List[Dict] = []
        self._load()

    def _load(self):
        sp = self.index_dir / "sections.jsonl"
        with sp.open() as f:
            for line in f:
                self.sections.append(json.loads(line))
        with (self.index_dir / "tfidf.pkl").open("rb") as f:
            self.vectorizer = pickle.load(f)
        self.matrix = sparse.load_npz(self.index_dir / "tfidf_matrix.npz")

        # Load BM25 if available
        self.bm25_model = None
        if BM25_AVAILABLE:
            bm25_tokens_path = self.index_dir / "bm25_tokens.npy"
            if bm25_tokens_path.exists():
                try:
                    corpus_tokens = np.load(bm25_tokens_path, allow_pickle=True)
                    self.bm25_model = BM25Okapi(corpus_tokens)
                except Exception as e:
                    print(f"Warning: Failed to load BM25 model: {e}")
            else:
                print("Warning: BM25 tokens not found, computing on-the-fly")
                self._build_bm25_on_fly()
        else:
            print("Warning: rank-bm25 not available, using TF-IDF only")

    def _build_bm25_on_fly(self):
        """Build BM25 model from sections if tokens not persisted."""
        if not BM25_AVAILABLE:
            return

        def tokenize_text(text: str) -> list[str]:
            return re.findall(r"[a-z0-9]+", text.lower())

        corpus_tokens = []
        for section in self.sections:
            text = f"{section.get('title', '')} {section.get('excerpt', '')} {section.get('text', '')}"
            tokens = tokenize_text(text)
            corpus_tokens.append(tokens)

        self.bm25_model = BM25Okapi(corpus_tokens)

    def stats(self):
        return {
            "total_sections": len(self.sections),
            "rfc_numbers": sorted({s["rfc_number"] for s in self.sections}),
        }

    def get_section(self, rfc: int, section: str) -> dict:
        """Get a full section by RFC number and section identifier.

        Args:
            rfc: RFC number
            section: Section identifier (e.g., "1", "1.1", "2.3")

        Returns:
            Full section dictionary including text/excerpt

        Raises:
            KeyError: If section not found
        """
        for s in self.sections:
            if s["rfc_number"] == rfc and s["section"] == section:
                return s
        raise KeyError(f"Section {section} not found in RFC {rfc}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        rfc_filter: Optional[List[int]] = None,
        mode: str = "hybrid",
    ):
        # Check cache first
        if CACHE_AVAILABLE:
            cache_key = f"search:{query}:{top_k}:{rfc_filter}:{mode}"
            cached_result = cache_get(cache_key)
            if cached_result is not None:
                return cached_result
        # Get weights from environment
        w_tfidf = float(os.getenv("HYBRID_W_TFIDF", "0.6"))
        w_bm25 = float(os.getenv("HYBRID_W_BM25", "0.4"))

        # TF-IDF scoring
        qv = self.vectorizer.transform([query])
        tfidf_scores = cosine_similarity(qv, self.matrix).ravel()

        # BM25 scoring
        bm25_scores = None
        if self.bm25_model and mode in ["bm25", "hybrid"]:

            def tokenize_query(q: str) -> list[str]:
                return re.findall(r"[a-z0-9]+", q.lower())

            query_tokens = tokenize_query(query)
            bm25_scores = self.bm25_model.get_scores(query_tokens)
            # Normalize BM25 scores to [0,1] with max-score scaling
            if len(bm25_scores) > 0:
                max_score = max(bm25_scores)
                if max_score > 0:
                    bm25_scores = [s / max_score for s in bm25_scores]

        # Combine scores based on mode
        if mode == "tfidf":
            final_scores = tfidf_scores
        elif mode == "bm25" and bm25_scores is not None:
            final_scores = np.array(bm25_scores)
        elif mode == "hybrid" and bm25_scores is not None:
            final_scores = w_tfidf * tfidf_scores + w_bm25 * np.array(bm25_scores)
        else:
            # Fallback to TF-IDF
            final_scores = tfidf_scores

        order = np.argsort(-final_scores)

        def _definitional_boost(sec: Dict, q: str) -> float:
            ql = q.lower()
            if any(k in ql for k in ("what is", "overview", "definition", "intro")):
                boost = 0.0
                title = (sec.get("title") or "").lower()
                section = sec.get("section", "")
                if title.startswith("introduction") or "overview" in title:
                    boost += 0.12
                if section == "1" or section.startswith("1."):
                    boost += 0.08
                if title.startswith(
                    ("intro", "overview", "definition", "terminology", "abstract")
                ):
                    boost += 0.05
                return boost
            return 0.0

        candidates: List[Tuple[Dict, float, Dict]] = []
        for i in order[:200]:  # light rerank window
            s = self.sections[int(i)]
            if rfc_filter and s["rfc_number"] not in rfc_filter:
                continue

            # Calculate subscores
            tfidf_score = float(tfidf_scores[int(i)])
            bm25_score = float(bm25_scores[int(i)]) if bm25_scores is not None else 0.0
            hybrid_score = float(final_scores[int(i)])

            # Apply definitional boost to hybrid score
            adj_score = hybrid_score + _definitional_boost(s, query)

            subscores = {
                "tfidf": tfidf_score,
                "bm25": bm25_score,
                "hybrid": hybrid_score,
            }

            candidates.append((s, adj_score, subscores))

        candidates.sort(key=lambda x: x[1], reverse=True)
        out = []
        for s, sc, subscores in candidates[:top_k]:
            out.append(
                {
                    "rfc": s["rfc_number"],
                    "section": s["section"],
                    "title": s["title"],
                    "score": float(sc),
                    "scores": subscores,
                }
            )

        # Cache the result
        if CACHE_AVAILABLE:
            cache_key = f"search:{query}:{top_k}:{rfc_filter}:{mode}"
            cache_set(cache_key, out)

        return out
