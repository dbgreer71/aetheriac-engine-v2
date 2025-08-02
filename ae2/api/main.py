from fastapi import FastAPI, Query
from pydantic import BaseModel
from pathlib import Path
from contextlib import asynccontextmanager
import hashlib
import json
import os
from ae2.retriever.index_store import IndexStore
try:
    from ae2.router.definitional_router import get_target_rfcs
except Exception:
    def get_target_rfcs(q: str): return []

AE_INDEX_DIR = Path(os.getenv("AE_INDEX_DIR", "data/index")).resolve()
AE_BIND_PORT = int(os.getenv("AE_BIND_PORT", "8001"))

store: IndexStore | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global store
    import logging
    logger = logging.getLogger(__name__)
    logger.info("AE v2 lifespan startup: loading index from %s", AE_INDEX_DIR)
    store = IndexStore(AE_INDEX_DIR)
    # load manifest and compute current hash for /debug/index
    manifest_path = AE_INDEX_DIR / "manifest.json"
    sections_path = AE_INDEX_DIR / "sections.jsonl"
    app.state.manifest = None
    app.state.root_hash = None
    if manifest_path.exists():
        app.state.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if sections_path.exists():
        h = hashlib.sha256()
        with sections_path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        app.state.root_hash = h.hexdigest()
    yield
    logger.info("AE v2 lifespan shutdown")

app = FastAPI(title="AE v2", lifespan=lifespan)

class QueryReq(BaseModel):
    query: str
    top_k: int = 3

@app.get("/healthz")
def healthz():
    manifest = getattr(app.state, "manifest", None)
    stats = store.stats() if store else {}
    return {"ok": True, "index_dir": str(AE_INDEX_DIR), 
            "total_sections": stats.get("total_sections"),
            "rfc_numbers": stats.get("rfc_numbers"),
            "manifest_present": bool(manifest)}

@app.get("/debug/explain")
def explain(query: str = Query(...)):
    targets = get_target_rfcs(query)
    hits = store.search(query, top_k=5, rfc_filter=targets or None)
    return {"router_decision": {"target_rfcs": targets},
            "top_hits": hits}

@app.get("/debug/index")
def debug_index():
    """Return manifest and live hash of sections.jsonl to verify integrity."""
    manifest = getattr(app.state, "manifest", None)
    live_hash = getattr(app.state, "root_hash", None)
    hash_match = (manifest and live_hash and manifest.get("root_hash") == live_hash)
    return {
        "index_dir": str(AE_INDEX_DIR),
        "manifest": manifest,
        "recomputed_root_hash": live_hash,
        "hash_match": bool(hash_match),
    }

@app.post("/query")
def query(req: QueryReq):
    targets = get_target_rfcs(req.query)
    hits = store.search(req.query, top_k=req.top_k, rfc_filter=targets or None)
    if not hits: return {"answer":"No relevant sections found.","citations":[]}
    s = hits[0]
    return {"answer": s.get("excerpt", s.get("title", ""))[:1200],
            "citations":[{"citation_text": f"RFC {s['rfc']} §{s['section']} — {s['title']}",
                          "url": f"https://www.rfc-editor.org/rfc/rfc{s['rfc']}.txt"}]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ae2.api.main:app", host="0.0.0.0", port=AE_BIND_PORT, reload=False)
