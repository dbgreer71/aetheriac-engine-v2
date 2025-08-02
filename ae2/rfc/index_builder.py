from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import re, json, pickle, hashlib, datetime as dt
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy import sparse

# Section headers must start at 1.. (not 0..). Match "1.", "1.2.", etc.
HEADER = re.compile(r"^(?P<num>(?:[1-9]\d*(?:\.\d+)*))\.\s+(?P<title>.+)$")

# --- Cleaning helpers --------------------------------------------------------
# dotted leaders with trailing page numbers e.g. "Equal-cost multipath .... 178"
TOC_DOTS = re.compile(r"\.{3,}\s*\d+\s*$")
# numeric "ruler" garbage lines like: "1 2 3 4 5 6 7 8 9 0 1 ..."
RULER_NUMS = re.compile(r"^(?:\d+\s+){8,}\d+$")
# ascii figure/ruler lines (boxes, separators)
ASCII_RULE = re.compile(r"^\s*[-=_+|]{3,}\s*$")
PLUS_MINUS_RUN = re.compile(r"^\s*(?:\+-){4,}.*$")
FIGURE_CAPTION = re.compile(r"^\s*Figure\s+\d+:\s*", re.IGNORECASE)
# RFC boilerplate headers
STATUS_MEMO = re.compile(r"^\s*Status of this Memo", re.IGNORECASE)
ABSTRACT = re.compile(r"^\s*Abstract", re.IGNORECASE)
COPYRIGHT = re.compile(r"^\s*Copyright", re.IGNORECASE)
# Table rulers and headers
TABLE_RULER = re.compile(r"^\s*[+\-]{3,}\s*$")

def clean_title(s: str) -> str:
    s = s.strip().strip('"').replace("\t", " ")
    s = TOC_DOTS.sub("", s).strip()
    s = re.sub(r"\s{2,}", " ", s)
    return s

def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

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
        sec = m.group("num")
        raw_title = m.group("title").strip()
        # Skip garbage headings like numeric "rulers"
        if RULER_NUMS.match(raw_title):
            continue
        title = clean_title(raw_title)
        
        raw_body = "\n".join(lines[start+1:end])
        # Drop ascii rulers/figures and collapse whitespace
        cleaned_lines = []
        for ln in raw_body.splitlines():
            if ASCII_RULE.match(ln) or PLUS_MINUS_RUN.match(ln):
                continue
            if RULER_NUMS.match(ln.strip()):
                continue
            if FIGURE_CAPTION.match(ln):
                continue
            if STATUS_MEMO.match(ln) or ABSTRACT.match(ln) or COPYRIGHT.match(ln):
                continue
            if TABLE_RULER.match(ln):
                continue
            cleaned_lines.append(ln)
        body = "\n".join(cleaned_lines).strip()
        
        if not title or not body:
            continue
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

    # Write/refresh manifest with root hash of sections.jsonl
    sec_path = output_dir / "sections.jsonl"
    manifest = {
        "built_at": dt.datetime.utcnow().isoformat()+"Z",
        "count_sections": len(sections),
        "rfc_numbers": sorted({s["rfc_number"] for s in sections}),
        "sections_path": str(sp),
        "artifacts": ["sections.jsonl","tfidf.pkl","tfidf_matrix.npz"],
        "root_hash": _hash_file(sec_path),
    }
    (output_dir/"manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
