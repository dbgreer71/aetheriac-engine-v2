from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import re
import json
import pickle
import hashlib
import datetime as dt
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
# ALL-CAPS headings (common in older RFCs like 826)
ALL_CAPS_HDR = re.compile(r"^[A-Z][A-Z0-9 \-/]{3,}$")

CANONICAL_826 = {
    "ADDRESS RESOLUTION PROTOCOL": "Address Resolution Protocol",
    "INTRODUCTION": "Introduction",
    "DISCUSSION": "Discussion",
    "PACKET FORMAT": "Packet format",
    "CONSIDERATIONS": "Considerations",
}


def clean_title(s: str) -> str:
    s = s.strip().strip('"').replace("\t", " ")
    s = TOC_DOTS.sub("", s).strip()
    s = re.sub(r"\s{2,}", " ", s)
    return s


def _maybe_canonicalize(rfc_number: int, title: str) -> str:
    if rfc_number == 826:
        t = title.upper().strip()
        if t in CANONICAL_826:
            return CANONICAL_826[t]
    return title


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(b: bytes) -> str:
    import hashlib

    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _parse_rfc_sections(text: str, rfc_number: int) -> List[Dict]:
    lines = text.splitlines()
    sections = []
    current = {"section": None, "title": None, "lines": []}
    pseudo_idx = 0

    for raw in lines:
        line = raw.rstrip("\n")

        # Skip noise lines
        if (
            ASCII_RULE.match(line)
            or PLUS_MINUS_RUN.match(line)
            or RULER_NUMS.match(line.strip())
            or FIGURE_CAPTION.match(line)
            or STATUS_MEMO.match(line)
            or ABSTRACT.match(line)
            or COPYRIGHT.match(line)
            or TABLE_RULER.match(line)
            or not line.strip()
        ):
            continue

        # Check for numbered section headers
        m = HEADER.match(line.strip())
        if m:
            # Flush previous section
            if current["title"] and current["lines"]:
                body = "\n".join(current["lines"]).strip()
                if body:
                    title = clean_title(
                        _maybe_canonicalize(rfc_number, current["title"])
                    )
                    sections.append(
                        {
                            "id": f"RFC{rfc_number}-{current['section']}",
                            "rfc_number": rfc_number,
                            "section": current["section"],
                            "title": title,
                            "url": f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt",
                            "text": body,
                            "excerpt": (body or title)[:1000],
                        }
                    )
            # Start new numbered section
            sec_id = m.group("num")
            current = {"section": sec_id, "title": line, "lines": []}
            continue

        # Check for ALL-CAPS headings (common in older RFCs like 826)
        if ALL_CAPS_HDR.match(line) and len(line.split()) <= 8:
            # Flush previous section
            if current["title"] and current["lines"]:
                body = "\n".join(current["lines"]).strip()
                if body:
                    title = clean_title(
                        _maybe_canonicalize(rfc_number, current["title"])
                    )
                    sections.append(
                        {
                            "id": f"RFC{rfc_number}-{current['section']}",
                            "rfc_number": rfc_number,
                            "section": current["section"],
                            "title": title,
                            "url": f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt",
                            "text": body,
                            "excerpt": (body or title)[:1000],
                        }
                    )
            # Start new pseudo-numbered section
            pseudo_idx += 1
            title = _maybe_canonicalize(rfc_number, line)
            current = {"section": str(pseudo_idx), "title": title, "lines": []}
            continue

        # Body content
        current["lines"].append(line)

    # Flush final section
    if current["title"] and current["lines"]:
        body = "\n".join(current["lines"]).strip()
        if body:
            sec = current["section"] or "0"
            # If we never saw a numbered section but have a heading, treat as §1 (intro)
            if sec == "0":
                sec = "1"
            title = clean_title(_maybe_canonicalize(rfc_number, current["title"]))
            sections.append(
                {
                    "id": f"RFC{rfc_number}-{sec}",
                    "rfc_number": rfc_number,
                    "section": sec,
                    "title": title,
                    "url": f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt",
                    "text": body,
                    "excerpt": (body or title)[:1000],
                }
            )

    # Fallback if no sections found
    if not sections:
        body = text.strip()
        return [
            {
                "id": f"RFC{rfc_number}",
                "rfc_number": rfc_number,
                "section": "1",
                "title": f"RFC {rfc_number}",
                "url": f"https://www.rfc-editor.org/rfc/rfc{rfc_number}.txt",
                "text": body,
                "excerpt": body[:1000],
            }
        ]

    return sections


def build_index(output_dir: Path, raw_dir: Path = Path("data/rfc_raw")) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    docs = []
    for p in sorted(raw_dir.glob("rfc*.txt")):
        try:
            n = int(p.stem.replace("rfc", ""))
        except ValueError:
            continue
        docs.append((n, p.read_text(errors="ignore")))
    if not docs:
        raise SystemExit(f"No RFC txt files found in {raw_dir.resolve()}")

    sections = []
    for n, txt in docs:
        sections.extend(_parse_rfc_sections(txt, n))

    sp = output_dir / "sections.jsonl"
    with sp.open("w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(s) + "\n")

    corpus = [
        (
            s.get("title", "") + " " + s.get("excerpt", "") + " " + s.get("text", "")
        ).strip()
        for s in sections
    ]
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, lowercase=True)
    X = vec.fit_transform(corpus)

    pickle.dump(vec, open(output_dir / "tfidf.pkl", "wb"))
    sparse.save_npz(output_dir / "tfidf_matrix.npz", X)

    # Write/refresh manifest with root hash of sections.jsonl
    sec_path = output_dir / "sections.jsonl"
    manifest = {
        "built_at": dt.datetime.utcnow().isoformat() + "Z",
        "count_sections": len(sections),
        "rfc_numbers": sorted({s["rfc_number"] for s in sections}),
        "sections_path": str(sp),
        "artifacts": ["sections.jsonl", "tfidf.pkl", "tfidf_matrix.npz"],
        "root_hash": _hash_file(sec_path),
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest
