from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json, pickle, numpy as np
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

class IndexStore:
    def __init__(self, index_dir: Path):
        self.index_dir = Path(index_dir)
        self.sections: List[Dict] = []
        self._load()

    def _load(self):
        sp = self.index_dir / "sections.jsonl"
        with sp.open() as f:
            for line in f: self.sections.append(json.loads(line))
        with (self.index_dir/"tfidf.pkl").open("rb") as f:
            self.vectorizer = pickle.load(f)
        self.matrix = sparse.load_npz(self.index_dir/"tfidf_matrix.npz")

    def stats(self):
        return {"total_sections": len(self.sections),
                "rfc_numbers": sorted({s["rfc_number"] for s in self.sections})}

    def search(self, query: str, top_k: int = 5, rfc_filter: Optional[List[int]] = None):
        qv = self.vectorizer.transform([query])
        scores = cosine_similarity(qv, self.matrix).ravel()
        order = np.argsort(-scores)

        def _definitional_boost(sec: Dict, q: str) -> float:
            ql = q.lower()
            if any(k in ql for k in ("what is", "overview", "definition", "intro")):
                boost = 0.0
                title = (sec.get("title") or "").lower()
                section = sec.get("section", "")
                if title.startswith("introduction") or "overview" in title:
                    boost += 0.05
                if section == "1" or section.startswith("1."):
                    boost += 0.03
                return boost
            return 0.0

        candidates: List[Tuple[Dict, float]] = []
        for i in order[:200]:  # light rerank window
            s = self.sections[int(i)]
            if rfc_filter and s["rfc_number"] not in rfc_filter: continue
            base = float(scores[int(i)])
            adj = base + _definitional_boost(s, query)
            candidates.append((s, adj))

        candidates.sort(key=lambda x: x[1], reverse=True)
        out = []
        for s, sc in candidates[:top_k]:
            out.append({
                "rfc": s["rfc_number"],
                "section": s["section"],
                "title": s["title"],
                "score": float(sc),
            })
        return out
