from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from pathlib import Path
from contextlib import asynccontextmanager
import hashlib
import json
import os
from typing import List, Optional, Dict
from ae2.retriever.index_store import IndexStore
from ae2.concepts.compiler import compile_concept
from ae2.concepts.store import ConceptStore
from ae2.concepts.errors import ConceptCompileError
from ae2.playbooks.models import PlayContext
from ae2.playbooks.engine import run_playbook, get_playbook_explanation
from ae2.router.router import route
from ae2.assembler.dispatcher import assemble

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

    # Initialize cache if enabled
    cache_enabled = os.getenv("AE_CACHE_ENABLED", "0").lower() in ("1", "true", "yes")
    if cache_enabled:
        try:
            from ae2.common.ttl_lru import init_cache

            cache_size = int(os.getenv("AE_CACHE_SIZE", "1000"))
            cache_ttl = int(os.getenv("AE_CACHE_TTL_S", "300"))
            init_cache(maxsize=cache_size, ttl_seconds=cache_ttl)
            logger.info("Cache initialized: size=%d, ttl=%ds", cache_size, cache_ttl)
        except ImportError:
            logger.warning("Cache module not available, continuing without cache")

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
            # Run GC to ensure accurate counts
            concept_store.gc_manifest()
            concepts = concept_store.list_concepts()
            concepts_count = len(concepts)
            concepts_root_hash = concept_store.get_root_hash()
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
def query(
    req: QueryReq,
    mode: str = Query("hybrid"),
    vendor: str = Query(None),
    iface: str = Query(None),
    area: str = Query(None),
    auth: str = Query(None),
    mtu: int = Query(None),
    pull: bool = Query(False),
):
    # Handle auto mode with unified router
    if mode == "auto":
        if store is None or concept_store is None:
            raise HTTPException(status_code=500, detail="Stores not initialized")

        # Prepare stores dictionary
        stores = {"index_store": store, "concept_store": concept_store}

        # Prepare parameters
        params = {}
        if vendor:
            params["vendor"] = vendor
        if iface:
            params["iface"] = iface
        if area:
            params["area"] = area
        if auth:
            params["auth"] = auth
        if mtu:
            params["mtu"] = mtu
        if pull:
            params["pull"] = pull

        # Route the query
        decision = route(req.query, stores)

        # Assemble the response
        result = assemble(decision, req.query, params, stores)

        # Add mode information
        result["mode"] = "auto"

        return result

    # Handle existing modes (tfidf, bm25, hybrid)
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
def compile_concept_endpoint(
    slug: str = Query(...), save: bool = Query(False), pull: bool = Query(False)
):
    """Compile a concept card for the given slug."""
    if store is None:
        raise HTTPException(status_code=500, detail="Index store not initialized")

    try:
        card = compile_concept(slug, store, concept_store)

        # Save to disk if requested
        if save:
            if concept_store is None:
                raise HTTPException(
                    status_code=500, detail="Concept store not initialized"
                )
            concept_store.save(card)

        # Handle pull-through compilation
        pulled = []
        pulled_errors = []
        if pull and save and concept_store:
            # Compile related concepts that are missing
            for related_slug in card.related:
                if not concept_store.exists(related_slug):
                    try:
                        related_card = compile_concept(
                            related_slug, store, concept_store
                        )
                        concept_store.save(related_card)
                        pulled.append(related_slug)
                    except ConceptCompileError as e:
                        pulled_errors.append(
                            {"slug": related_slug, "code": e.code, "message": e.msg}
                        )
                    except Exception as e:
                        pulled_errors.append(
                            {
                                "slug": related_slug,
                                "code": "UNKNOWN_ERROR",
                                "message": str(e),
                            }
                        )

        response = card.model_dump()
        if pull:
            response["pulled"] = pulled
            response["pulled_errors"] = pulled_errors

        return response
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


@app.get("/concepts/list")
def list_concepts():
    """List all concepts with manifest data."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        # Get current index root hash for stale detection
        current_index_root_hash = getattr(app.state, "root_hash", None)

        return concept_store.list_concepts_with_stale(current_index_root_hash)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/concepts/rebuild")
def rebuild_concept(slug: str = Query(...)):
    """Rebuild a concept card from the current index."""
    if store is None:
        raise HTTPException(status_code=500, detail="Index store not initialized")
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        # Recompile the card
        card = compile_concept(slug, store, concept_store)

        # Save the rebuilt card (this will overwrite the existing file)
        concept_store.save(card)

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


@app.delete("/concepts/{slug}")
def delete_concept(slug: str):
    """Delete a concept card by slug."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        deleted = concept_store.delete_card(slug)
        if deleted:
            return {"ok": True}
        else:
            # Return 204 for idempotent delete (card didn't exist)
            from fastapi import Response

            return Response(status_code=204)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concepts/schema")
def get_concept_schema():
    """Get JSON schema for concept cards."""
    from ae2.concepts.models import ConceptCard

    return ConceptCard.model_json_schema()


@app.get("/concepts/validate/{slug}")
def validate_concept_references(slug: str):
    """Validate references for a concept card."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        return concept_store.validate_references(slug)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Concept card not found: {slug}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concepts/search")
def search_concepts(
    q: str = Query(...), limit: int = Query(10), offset: int = Query(0)
):
    """Search persisted concept cards."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    from ae2.concepts.search import search_cards

    try:
        # Get all cards
        cards = concept_store.get_all_cards()

        # Get current index root hash for stale resolution
        current_index_root_hash = getattr(app.state, "root_hash", None)

        def stale_resolver(slug: str) -> bool:
            """Resolve stale flag for a slug."""
            if current_index_root_hash is None:
                return False

            try:
                card = concept_store.load(slug)
                stored_hash = card.provenance.index_root_hash
                return stored_hash != current_index_root_hash
            except Exception:
                return True

        # Search cards
        total, items = search_cards(cards, q, limit, offset, stale_resolver)

        return {"total": total, "items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concepts/tags")
def get_concept_tags():
    """Get tag counts for all concepts."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        tag_counts = concept_store.get_tag_counts()
        return {"tags": tag_counts}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class CompileManyRequest(BaseModel):
    slugs: List[str]
    mode: str = "hybrid"


class ExportRequest(BaseModel):
    slugs: Optional[List[str]] = None


@app.post("/concepts/compile_many")
def compile_many_concepts(request: CompileManyRequest, save: bool = Query(False)):
    """Compile multiple concept cards with bounded concurrency."""
    if store is None:
        raise HTTPException(status_code=500, detail="Index store not initialized")
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    from concurrent.futures import ThreadPoolExecutor

    # Compile concepts with bounded concurrency
    results = []
    saved_count = 0

    def compile_single(slug: str) -> Dict[str, any]:
        try:
            card = compile_concept(slug, store, None)  # Don't save yet
            card_dict = card.model_dump()

            # Save if requested
            if save:
                concept_store.save(card)
                return {
                    "slug": slug,
                    "status": "ok",
                    "id": card.id,
                    "sha256": concept_store._compute_card_hash(card_dict),
                    "saved": True,
                }
            else:
                return {
                    "slug": slug,
                    "status": "ok",
                    "id": card.id,
                    "sha256": concept_store._compute_card_hash(card_dict),
                    "saved": False,
                }
        except ConceptCompileError as e:
            return {
                "slug": slug,
                "status": "error",
                "error": {"code": e.code, "message": e.msg},
            }
        except Exception as e:
            return {
                "slug": slug,
                "status": "error",
                "error": {"code": "UNKNOWN_ERROR", "message": str(e)},
            }

    # Use thread pool for bounded concurrency
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(compile_single, slug) for slug in request.slugs]
        results = [future.result() for future in futures]

    # Count saved items
    saved_count = sum(1 for result in results if result.get("saved", False))

    return {"ok": True, "results": results, "saved_count": saved_count}


@app.post("/concepts/export")
def export_concepts(request: ExportRequest = None):
    """Export concepts to a ZIP file."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    from fastapi.responses import Response

    # Get slugs from request (None means export all)
    slugs = request.slugs if request else None

    # Export concepts
    try:
        zip_data = concept_store.export_concepts(slugs)

        return Response(
            content=zip_data,
            media_type="application/zip",
            headers={
                "Content-Disposition": 'attachment; filename="concepts_export.zip"'
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.get("/concepts/diff/{slug}")
def get_concept_diff(slug: str, recompile: bool = Query(True)):
    """Get diff between stored and current concept card."""
    if store is None:
        raise HTTPException(status_code=500, detail="Index store not initialized")
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    from ae2.concepts.diff import card_diff

    try:
        # Load the stored card
        stored_card = concept_store.load(slug)
        stored_dict = stored_card.model_dump()

        if recompile:
            # Compile current card from live index
            current_card = compile_concept(slug, store, None)  # Don't save
            current_dict = current_card.model_dump()
        else:
            # Return empty diff (stored vs stored)
            current_dict = stored_dict

        # Compute diff
        diff_result = card_diff(stored_dict, current_dict)

        # Add provenance information
        stored_index_hash = stored_card.provenance.index_root_hash
        live_index_hash = getattr(app.state, "root_hash", None)

        diff_result["provenance"] = {
            "stored_index": stored_index_hash,
            "live_index": live_index_hash,
        }

        return diff_result

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Concept card not found: {slug}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/concepts/{slug}")
def get_concept_by_slug(slug: str):
    """Get a concept card by slug."""
    if concept_store is None:
        raise HTTPException(status_code=500, detail="Concept store not initialized")

    try:
        card = concept_store.load(slug)
        card_dict = card.model_dump()

        # Add stale flag
        current_index_root_hash = getattr(app.state, "root_hash", None)

        if current_index_root_hash is not None:
            stored_hash = card.provenance.index_root_hash
            card_dict["stale"] = stored_hash != current_index_root_hash
        else:
            card_dict["stale"] = False

        return card_dict
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Concept card not found: {slug}")
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


@app.post("/troubleshoot/ospf-neighbor")
def troubleshoot_ospf_neighbor(ctx: PlayContext):
    """Execute OSPF neighbor-down troubleshooting playbook."""
    if store is None:
        raise HTTPException(status_code=500, detail="Index store not initialized")

    try:
        result = run_playbook("ospf-neighbor-down", ctx, store)
        return {
            "playbook_id": result.playbook_id,
            "steps": [step.model_dump() for step in result.steps],
            "debug": {"matched_rules": len(result.steps), "vendor": ctx.vendor},
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/explain_playbook")
def explain_playbook(slug: str = Query(...), vendor: str = Query(...)):
    """Get explanation of a playbook's rules and commands."""
    try:
        explanation = get_playbook_explanation(slug, vendor)
        return explanation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/route")
def debug_route(query: str = Query(...)):
    """Get routing decision for a query without assembly."""
    if store is None or concept_store is None:
        raise HTTPException(status_code=500, detail="Stores not initialized")

    try:
        stores = {"index_store": store, "concept_store": concept_store}

        decision = route(query, stores)

        return {
            "query": query,
            "intent": decision.intent,
            "target": decision.target,
            "confidence": decision.confidence,
            "matches": decision.matches,
            "notes": decision.notes,
            "mode_used": decision.mode_used,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ae2.api.main:app", host="0.0.0.0", port=AE_BIND_PORT, reload=False)
