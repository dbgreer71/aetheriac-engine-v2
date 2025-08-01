"""
Hybrid retrieval and ranking system.

This module implements a hybrid retrieval system that combines dense embeddings
with BM25 sparse retrieval for improved search performance and relevance.
"""

import logging
from typing import Dict, List, Optional, Tuple

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from ..contracts.models import RFCSection
from ..contracts.settings import settings

logger = logging.getLogger(__name__)


class HybridRanker:
    """Hybrid ranking system combining dense and sparse retrieval."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.hybrid_ranker")
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.bm25_index: Optional[BM25Okapi] = None
        self.dense_embeddings: Optional[np.ndarray] = None
        self.documents: List[RFCSection] = []
        self.hybrid_weight = settings.hybrid_weight
        
        self.logger.info(f"Initialized hybrid ranker with model: {settings.embedding_model}")
    
    def build_index(self, documents: List[RFCSection]) -> None:
        """Build both dense and sparse indexes from documents."""
        self.documents = documents
        self.logger.info(f"Building indexes for {len(documents)} documents")
        
        # Prepare text for indexing
        texts = [doc.excerpt for doc in documents]
        tokenized_texts = [text.lower().split() for text in texts]
        
        # Build BM25 index
        self.bm25_index = BM25Okapi(
            tokenized_texts,
            k1=settings.bm25_k1,
            b=settings.bm25_b
        )
        
        # Build dense embeddings
        self.dense_embeddings = self.embedding_model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32,
            normalize_embeddings=True
        )
        
        self.logger.info("Index building completed")
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        dense_weight: Optional[float] = None
    ) -> List[Tuple[RFCSection, float]]:
        """Perform hybrid search combining dense and sparse retrieval."""
        if not self.documents or self.bm25_index is None or self.dense_embeddings is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        # Use provided weight or default
        weight = dense_weight if dense_weight is not None else self.hybrid_weight
        
        # Dense retrieval
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        )[0]
        
        dense_scores = np.dot(self.dense_embeddings, query_embedding)
        
        # Sparse retrieval (BM25)
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25_index.get_scores(tokenized_query)
        
        # Normalize scores to [0, 1] range
        dense_scores_norm = (dense_scores - dense_scores.min()) / (dense_scores.max() - dense_scores.min() + 1e-8)
        bm25_scores_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-8)
        
        # Combine scores
        hybrid_scores = weight * dense_scores_norm + (1 - weight) * bm25_scores_norm
        
        # Get top-k results
        top_indices = np.argsort(hybrid_scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            document = self.documents[idx]
            score = float(hybrid_scores[idx])
            results.append((document, score))
        
        self.logger.debug(f"Hybrid search returned {len(results)} results for query: {query}")
        return results
    
    def search_dense_only(self, query: str, top_k: int = 10) -> List[Tuple[RFCSection, float]]:
        """Perform dense-only search."""
        if not self.documents or self.dense_embeddings is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        query_embedding = self.embedding_model.encode(
            [query],
            normalize_embeddings=True
        )[0]
        
        scores = np.dot(self.dense_embeddings, query_embedding)
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            document = self.documents[idx]
            score = float(scores[idx])
            results.append((document, score))
        
        return results
    
    def search_sparse_only(self, query: str, top_k: int = 10) -> List[Tuple[RFCSection, float]]:
        """Perform sparse-only search."""
        if not self.documents or self.bm25_index is None:
            raise ValueError("Index not built. Call build_index() first.")
        
        tokenized_query = query.lower().split()
        scores = self.bm25_index.get_scores(tokenized_query)
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            document = self.documents[idx]
            score = float(scores[idx])
            results.append((document, score))
        
        return results
    
    def get_document_by_id(self, doc_id: str) -> Optional[RFCSection]:
        """Get document by its ID."""
        for doc in self.documents:
            if doc.id == doc_id:
                return doc
        return None
    
    def get_index_stats(self) -> Dict[str, any]:
        """Get statistics about the built index."""
        if not self.documents:
            return {"error": "No documents indexed"}
        
        return {
            "document_count": len(self.documents),
            "embedding_dimension": self.dense_embeddings.shape[1] if self.dense_embeddings is not None else None,
            "rfc_numbers": sorted(list(set(doc.rfc_number for doc in self.documents))),
            "hybrid_weight": self.hybrid_weight,
            "embedding_model": settings.embedding_model,
        } 