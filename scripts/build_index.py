from pathlib import Path
import re
import json
import numpy as np
from ae2.rfc.index_builder import build_index

def tokenize_text(text: str) -> list[str]:
    """Simple, deterministic tokenizer for BM25."""
    return re.findall(r"[a-z0-9]+", text.lower())

if __name__ == "__main__":
    out = Path("data/index"); out.mkdir(parents=True, exist_ok=True)
    m = build_index(output_dir=out)
    
    # Persist BM25 tokens
    sections_path = out / "sections.jsonl"
    if sections_path.exists():
        import json
        sections = []
        with sections_path.open() as f:
            for line in f:
                sections.append(json.loads(line))
        
        # Tokenize each section
        corpus_tokens = []
        for section in sections:
            text = f"{section.get('title', '')} {section.get('excerpt', '')} {section.get('text', '')}"
            tokens = tokenize_text(text)
            corpus_tokens.append(tokens)
        
        # Save tokens and metadata
        np.save(out / "bm25_tokens.npy", np.array(corpus_tokens, dtype=object))
        bm25_meta = {
            "section_count": len(sections),
            "tokenizer_version": "simple_regex",
            "tokenizer_pattern": r"[a-z0-9]+"
        }
        with (out / "bm25_meta.json").open("w") as f:
            json.dump(bm25_meta, f, indent=2)
        
        print(f"[OK] BM25 tokens persisted: {len(corpus_tokens)} sections")
    
    print(f"[OK] Index built at {out.resolve()} with {m.get('count_sections')} sections")
