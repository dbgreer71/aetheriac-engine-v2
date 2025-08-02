from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
from contextlib import asynccontextmanager
import hashlib
import json
import os
from ae2.retriever.index_store import IndexStore
from ae2.concepts.compiler import compile_concept
from ae2.concepts.store import ConceptStore
from ae2.concepts.errors import ConceptCompileError

try:
    from ae2.router.definitional_router import get_target_rfcs
except Exception:

    def get_target_rfcs(q: str):
        return []


AE_INDEX_DIR = Path(os.getenv("AE_INDEX_DIR", "data/index")).resolve()
AE_BIND_PORT = int(os.getenv("AE_BIND_PORT", "8001"))

store: IndexStore | None = None
concept_store: ConceptStore | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global store, concept_store
    import logging

    logger = logging.getLogger(__name__)
    logger.info("AE v2 lifespan startup: loading index from %s", AE_INDEX_DIR)
    store = IndexStore(AE_INDEX_DIR)
    concept_store = ConceptStore()
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
    return {
        "ok": True,
        "index_dir": str(AE_INDEX_DIR),
        "total_sections": stats.get("total_sections"),
        "rfc_numbers": stats.get("rfc_numbers"),
        "manifest_present": bool(manifest),
    }


@app.get("/debug/explain")
def explain(query: str = Query(...), mode: str = Query("hybrid")):
    targets = get_target_rfcs(query)
    hits = store.search(query, top_k=5, rfc_filter=targets or None, mode=mode)
    return {"router_decision": {"target_rfcs": targets, "mode": mode}, "top_hits": hits}


@app.get("/debug/index")
def debug_index():
    """Return manifest and live hash of sections.jsonl to verify integrity."""
    manifest = getattr(app.state, "manifest", None)
    live_hash = getattr(app.state, "root_hash", None)
    hash_match = manifest and live_hash and manifest.get("root_hash") == live_hash

    # Calculate concept counts and hash
    concepts_count = 0
    concepts_root_hash = None
    if concept_store:
        try:
            concept_ids = concept_store.list_ids()
            concepts_count = len(concept_ids)

            # Compute hash over all concept card JSONs (sorted for determinism)
            if concepts_count > 0:
                import hashlib

                h = hashlib.sha256()
                for card_id in sorted(concept_ids):
                    card = concept_store.load(card_id)
                    # Hash the card's JSON representation
                    card_json = card.model_dump_json()
                    h.update(card_json.encode("utf-8"))
                concepts_root_hash = h.hexdigest()
        except Exception:
            # If concept store fails, continue with defaults
            pass

    return {
        "index_dir": str(AE_INDEX_DIR),
        "manifest": manifest,
        "recomputed_root_hash": live_hash,
        "hash_match": bool(hash_match),
        "concepts_count": concepts_count,
        "concepts_root_hash": concepts_root_hash,
    }


@app.post("/query")
def query(req: QueryReq, mode: str = Query("hybrid")):
    targets = get_target_rfcs(req.query)
    hits = store.search(
        req.query, top_k=req.top_k, rfc_filter=targets or None, mode=mode
    )
    if not hits:
        return {"answer": "No relevant sections found.", "citations": [], "mode": mode}
    s = hits[0]
    return {
        "answer": s.get("excerpt", s.get("title", ""))[:1200],
        "citations": [
            {
                "citation_text": f"RFC {s['rfc']} §{s['section']} — {s['title']}",
                "url": f"https://www.rfc-editor.org/rfc/rfc{s['rfc']}.txt",
            }
        ],
        "mode": mode,
        "debug": {"score": s.get("score"), "scores": s.get("scores", {})},
    }


@app.post("/concepts/compile")
def compile_concept_endpoint(slug: str = Query(...)):
    """Compile a concept card for the given slug."""
    if store is None:
        raise HTTPException(status_code=500, detail="Index store not initialized")

    try:
        card = compile_concept(slug, store, concept_store)
        return card.model_dump()
    except ConceptCompileError as e:
        # Return structured error information for concept compilation errors
        raise HTTPException(
            status_code=400,
            detail={
                "error": "concept_compile_error",
                "code": e.code,
                "message": e.msg,
                "slug": slug,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/concepts/{card_id}")
def get_concept(card_id: str):
    """Get a concept card by ID."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        card = concept_store.load(card_id)
        return card.model_dump()
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Concept card not found: {card_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/concept/{card_id}")
def debug_concept(card_id: str):
    """Get a concept card with retrieval trace for debugging."""
    if store is None or concept_store is None:
        raise HTTPException(status_code=500, detail="Stores not initialized")

    try:
        card = concept_store.load(card_id)

        # Extract the slug from the card ID
        slug = card_id.split(":")[1] if ":" in card_id else card_id

        # Get the retrieval trace
        targets = get_target_rfcs(slug)
        hits = store.search(slug, top_k=5, rfc_filter=targets or None, mode="hybrid")

        return {
            "card": card.model_dump(),
            "retrieval_trace": {"slug": slug, "target_rfcs": targets, "top_hits": hits},
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"Concept card not found: {card_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concepts")
def list_concepts():
    """List all available concept card IDs."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        return {"concept_ids": concept_store.list_ids()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ae2.api.main:app", host="0.0.0.0", port=AE_BIND_PORT, reload=False)
