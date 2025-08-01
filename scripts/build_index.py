from pathlib import Path
from ae2.rfc.index_builder import build_index
if __name__ == "__main__":
    out = Path("data/index"); out.mkdir(parents=True, exist_ok=True)
    m = build_index(output_dir=out)
    print(f"[OK] Index built at {out.resolve()} with {m.get('count_sections')} sections")
