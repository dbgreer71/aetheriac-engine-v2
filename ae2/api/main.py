"""
FastAPI application for AE v2.

This module implements the main FastAPI application with query endpoints,
debug functionality, and health checks.
"""

import logging
import time
from typing import Dict, List, Optional

import orjson
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from ..assembler.definition_assembler import DefinitionAssembler
from ..contracts.models import Query, QueryResponse, QueryType
from ..contracts.settings import settings
from ..retriever.hybrid_ranker import HybridRanker
from ..router.definitional_router import DefinitionalRouter
from ..storage.index_builder import IndexBuilder

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format=settings.log_format
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Aetheriac Engine v2 - Network knowledge retrieval system",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global components
ranker: Optional[HybridRanker] = None
router: Optional[DefinitionalRouter] = None
assembler: Optional[DefinitionAssembler] = None
index_builder: Optional[IndexBuilder] = None


class QueryRequest(BaseModel):
    """Request model for queries."""
    text: str
    query_type: Optional[QueryType] = None
    context: Optional[Dict] = None


class QueryResponseModel(BaseModel):
    """Response model for queries."""
    query_id: str
    response_type: QueryType
    content: Dict
    citations: List[str]
    confidence: float
    processing_time_ms: float
    created_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    components: Dict[str, str]
    index_stats: Optional[Dict] = None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global ranker, router, assembler, index_builder
    
    logger.info("Starting AE v2 API")
    
    try:
        # Ensure directories exist
        settings.ensure_directories()
        
        # Initialize components
        ranker = HybridRanker()
        router = DefinitionalRouter()
        assembler = DefinitionAssembler()
        index_builder = IndexBuilder()
        
        # Build index if it doesn't exist
        if not index_builder.index_exists():
            logger.info("Building index from RFC sections")
            await index_builder.build_index()
        
        # Load index into ranker
        documents = index_builder.load_documents()
        if documents:
            ranker.build_index(documents)
            logger.info(f"Loaded {len(documents)} documents into ranker")
        else:
            logger.warning("No documents loaded into ranker")
        
        logger.info("AE v2 API startup completed")
        
    except Exception as e:
        logger.error(f"Failed to start AE v2 API: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down AE v2 API")


@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    components = {
        "ranker": "ready" if ranker else "not_initialized",
        "router": "ready" if router else "not_initialized",
        "assembler": "ready" if assembler else "not_initialized",
        "index_builder": "ready" if index_builder else "not_initialized",
    }
    
    index_stats = None
    if ranker:
        index_stats = ranker.get_index_stats()
    
    return HealthResponse(
        status="healthy" if all(c == "ready" for c in components.values()) else "degraded",
        version=settings.app_version,
        components=components,
        index_stats=index_stats,
    )


@app.post("/query", response_model=QueryResponseModel)
async def query(request: QueryRequest):
    """Main query endpoint."""
    if not ranker or not router or not assembler:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    start_time = time.time() * 1000
    
    try:
        # Create query object
        query_obj = Query(
            text=request.text,
            query_type=request.query_type,
            context=request.context or {}
        )
        
        # Route query
        routing_info = router.route_query(query_obj)
        
        # Retrieve relevant sections
        retrieved_sections = ranker.search(
            query=query_obj.text,
            top_k=10,
            dense_weight=routing_info.get("dense_weight")
        )
        
        # Generate query ID
        query_id = f"query_{int(time.time() * 1000)}"
        
        # Assemble response based on query type
        if query_obj.query_type == QueryType.DEFINITION:
            response = assembler.assemble_definition(
                query=query_obj,
                retrieved_sections=retrieved_sections,
                query_id=query_id
            )
        else:
            # For now, fall back to definition assembler
            # TODO: Implement concept and troubleshooting assemblers
            response = assembler.assemble_definition(
                query=query_obj,
                retrieved_sections=retrieved_sections,
                query_id=query_id
            )
        
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@app.get("/debug/index")
async def debug_index():
    """Debug endpoint for index information."""
    if not ranker:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    stats = ranker.get_index_stats()
    return {
        "index_stats": stats,
        "router_stats": router.get_router_stats() if router else None,
        "assembler_stats": assembler.get_assembler_stats() if assembler else None,
    }


@app.get("/debug/explain/{query_id}")
async def debug_explain(query_id: str):
    """Debug endpoint for explaining query processing."""
    # TODO: Implement query explanation with intermediate results
    return {
        "query_id": query_id,
        "explanation": "Query explanation not yet implemented",
        "intermediate_results": {},
    }


@app.post("/debug/search")
async def debug_search(request: QueryRequest):
    """Debug endpoint for raw search results."""
    if not ranker:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    try:
        # Perform search
        results = ranker.search(query=request.text, top_k=10)
        
        # Format results
        formatted_results = []
        for section, score in results:
            formatted_results.append({
                "rfc_number": section.rfc_number,
                "section": section.section,
                "title": section.title,
                "excerpt": section.excerpt[:200] + "..." if len(section.excerpt) > 200 else section.excerpt,
                "url": section.url,
                "score": score,
                "hash": section.hash,
            })
        
        return {
            "query": request.text,
            "results": formatted_results,
            "total_results": len(formatted_results),
        }
        
    except Exception as e:
        logger.error(f"Debug search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Debug search failed: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
        }
    )


def main():
    """Main entry point for the API server."""
    import uvicorn
    
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"API will be available at http://{settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "ae2.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
    )


if __name__ == "__main__":
    main() 