from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Optional
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
        out = []
        for i in order:
            s = self.sections[int(i)]
            if rfc_filter and s["rfc_number"] not in rfc_filter: continue
            out.append((s, float(scores[int(i)])))
            if len(out) >= top_k: break
        return out
