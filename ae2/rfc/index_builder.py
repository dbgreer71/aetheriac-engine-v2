from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import re, json, pickle, hashlib, datetime as dt
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy import sparse

HEADER = re.compile(r"^(?P<num>\d+(?:\.\d+)*)\s+(?P<title>.+)$")

def _sha256_bytes(b: bytes) -> str:
    import hashlib
    h = hashlib.sha256(); h.update(b); return h.hexdigest()

def _parse_rfc_sections(text: str, rfc_number: int) -> List[Dict]:
    lines = text.splitlines()
    idx = [i for i,l in enumerate(lines) if HEADER.match(l.strip())]
    if not idx:
        body = text.strip()
        return [{
            "id": f"RFC{rfc_number}",
            "rfc_number": rfc_number,
            "section": "0",
            "title": f"RFC {rfc_number}",
            "url": f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt",
            "text": body,
            "excerpt": body[:1000]
        }]
    idx.append(len(lines))
    sections = []
    for i in range(len(idx)-1):
        start, end = idx[i], idx[i+1]
        m = HEADER.match(lines[start].strip())
        if not m: continue
        sec = m.group("num"); title = m.group("title").strip()
        body = "\n".join(lines[start+1:end]).strip()
        sections.append({
            "id": f"RFC{rfc_number}-{sec}",
            "rfc_number": rfc_number,
            "section": sec,
            "title": title,
            "url": f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt",
            "text": body,
            "excerpt": (body or title)[:1000]
        })
    return sections

def build_index(output_dir: Path, raw_dir: Path = Path("data/rfc_raw")) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    docs = []
    for p in sorted(raw_dir.glob("rfc*.txt")):
        try: n = int(p.stem.replace("rfc",""))
        except: continue
        docs.append((n, p.read_text(errors="ignore")))
    if not docs:
        raise SystemExit(f"No RFC txt files found in {raw_dir.resolve()}")

    sections = []
    for n, txt in docs:
        sections.extend(_parse_rfc_sections(txt, n))

    sp = output_dir / "sections.jsonl"
    with sp.open("w", encoding="utf-8") as f:
        for s in sections: f.write(json.dumps(s) + "\n")

    corpus = [(s.get("title","")+" "+s.get("excerpt","")+" "+s.get("text","")).strip()
              for s in sections]
    vec = TfidfVectorizer(ngram_range=(1,2), min_df=1, lowercase=True)
    X = vec.fit_transform(corpus)
    import pickle; pickle.dump(vec, open(output_dir/"tfidf.pkl","wb"))
    sparse.save_npz(output_dir/"tfidf_matrix.npz", X)

    manifest = {
        "built_at": dt.datetime.utcnow().isoformat()+"Z",
        "count_sections": len(sections),
        "rfc_numbers": sorted({s["rfc_number"] for s in sections}),
        "sections_path": str(sp),
        "artifacts": ["sections.jsonl","tfidf.pkl","tfidf_matrix.npz"]
    }
    (output_dir/"manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
