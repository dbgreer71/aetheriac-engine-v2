#!/usr/bin/env python3
"""
Clean RAG Backend for Aetheriac Engine
Connects to the actual vector store and web search system without authentication
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import time

# Import only the essential RAG components
from config.settings import RAGConfig
from vectorizer.vectorizer import VectorStore
from providers.web_search import WebSearchFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the real RAG system
config = RAGConfig()
vector_store = VectorStore(config)
web_search = WebSearchFactory.create_web_search_provider()

# Create FastAPI app
app = FastAPI(
    title="Aetheriac Engine - Clean RAG Backend",
    description="Professional Network Engineering AI Assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response models
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    response_time: float
    search_method: str

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Aetheriac Engine RAG Backend",
        "vector_store_snippets": len(vector_store.store.snippet_metadata),
        "web_search_available": web_search is not None
    }

@app.get("/")
async def root():
    """Root endpoint with system info"""
    return {
        "service": "Aetheriac Engine",
        "description": "Professional Network Engineering AI Assistant",
        "version": "1.0.0",
        "status": "operational",
        "vector_store_snippets": len(vector_store.store.snippet_metadata)
    }

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Main query endpoint using real RAG system"""
    start_time = time.time()
    
    try:
        logger.info(f"Processing query: {request.query}")
        
        # First try vector store search
        vector_results = vector_store.search(request.query, top_k=request.top_k, similarity_threshold=0.05)
        
        if vector_results:
            # Use vector store results
            snippets = [snippet for snippet, score in vector_results]
            answer = "\n\n".join([snippet.content for snippet in snippets])
            sources = [snippet.source for snippet in snippets if hasattr(snippet, 'source') and snippet.source]
            confidence = min(1.0, sum(score for _, score in vector_results) / len(vector_results))
            search_method = "vector_store"
            
            logger.info(f"Found {len(vector_results)} results in vector store")
        else:
            # Fall back to web search
            logger.info(f"No vector store results, trying web search")
            web_results = web_search.search(request.query, request.top_k)
            
            if not web_results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No relevant data found for query: '{request.query}'. The system must find information from reliable sources to answer this question."
                )
            
            # Convert web results to answer - FIXED CONTENT EXTRACTION
            answer_parts = []
            sources = []
            
            for result in web_results:
                # Debug: Log the result structure
                logger.info(f"Web result type: {type(result)}, attributes: {dir(result)}")
                
                # Extract content from WebSearchResult fields
                content = None
                if hasattr(result, 'snippet') and result.snippet:
                    content = result.snippet
                elif hasattr(result, 'title') and result.title:
                    content = result.title
                elif hasattr(result, 'content') and result.content:
                    content = result.content
                elif hasattr(result, 'text') and result.text:
                    content = result.text
                elif hasattr(result, 'body') and result.body:
                    content = result.body
                elif hasattr(result, 'description') and result.description:
                    content = result.description
                
                # Extract source from WebSearchResult fields
                source = None
                if hasattr(result, 'url') and result.url:
                    source = result.url
                elif hasattr(result, 'source') and result.source:
                    source = result.source
                elif hasattr(result, 'link') and result.link:
                    source = result.link
                
                if content:
                    answer_parts.append(content)
                if source:
                    sources.append(source)
            
            # If we still don't have content, try to extract from the raw result
            if not answer_parts and web_results:
                for result in web_results:
                    # Try to convert the result to string
                    try:
                        if isinstance(result, dict):
                            # Handle dictionary results
                            if 'snippet' in result:
                                answer_parts.append(result['snippet'])
                            elif 'title' in result:
                                answer_parts.append(result['title'])
                            elif 'content' in result:
                                answer_parts.append(result['content'])
                            elif 'text' in result:
                                answer_parts.append(result['text'])
                            
                            if 'url' in result:
                                sources.append(result['url'])
                            elif 'source' in result:
                                sources.append(result['source'])
                        elif isinstance(result, str):
                            # Handle string results
                            answer_parts.append(result)
                        else:
                            # Try to get string representation
                            answer_parts.append(str(result))
                    except Exception as e:
                        logger.warning(f"Failed to extract content from result: {e}")
            
            answer = "\n\n".join(answer_parts) if answer_parts else "No content available from web search"
            confidence = 0.8  # Web search confidence
            search_method = "web_search"
            
            logger.info(f"Found {len(web_results)} results from web search, extracted {len(answer_parts)} content parts")
        
        response_time = time.time() - start_time
        
        return QueryResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            response_time=response_time,
            search_method=search_method
        )
        
    except Exception as e:
        logger.error(f"Error processing query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "vector_store_snippets": len(vector_store.store.snippet_metadata),
        "web_search_provider": type(web_search).__name__ if web_search else "None",
        "system_status": "operational"
    }

if __name__ == "__main__":
    logger.info("Starting Aetheriac Engine Clean RAG Backend...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info") 