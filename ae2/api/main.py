from fastapi import FastAPI, Query
from pydantic import BaseModel
from pathlib import Path
import os
from ae2.retriever.index_store import IndexStore
try:
    from ae2.router.definitional_router import get_target_rfcs
except Exception:
    def get_target_rfcs(q: str): return []

AE_INDEX_DIR = Path(os.getenv("AE_INDEX_DIR", "data/index")).resolve()
AE_BIND_PORT = int(os.getenv("AE_BIND_PORT", "8001"))

app = FastAPI(title="AE v2")

@app.on_event("startup")
def startup():
    app.state.store = IndexStore(AE_INDEX_DIR)

class QueryReq(BaseModel):
    query: str
    top_k: int = 3

@app.get("/healthz")
def healthz():
    st = app.state.store.stats()
    return {"ok": True, "index_dir": str(AE_INDEX_DIR), **st}

@app.get("/debug/explain")
def explain(query: str = Query(...)):
    targets = get_target_rfcs(query)
    hits = app.state.store.search(query, top_k=5, rfc_filter=targets or None)
    return {"router_decision": {"target_rfcs": targets},
            "top_hits": [{"rfc": s["rfc_number"], "section": s["section"], "title": s["title"], "score": sc}
                         for s, sc in hits]}

@app.post("/query")
def query(req: QueryReq):
    targets = get_target_rfcs(req.query)
    hits = app.state.store.search(req.query, top_k=req.top_k, rfc_filter=targets or None)
    if not hits: return {"answer":"No relevant sections found.","citations":[]}
    s, _ = hits[0]
    return {"answer": s["excerpt"] or s["title"],
            "citations":[{"citation_text": f"RFC {s['rfc_number']} §{s['section']} — {s['title']}",
                          "url": s["url"]}]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("ae2.api.main:app", host="0.0.0.0", port=AE_BIND_PORT, reload=False)
