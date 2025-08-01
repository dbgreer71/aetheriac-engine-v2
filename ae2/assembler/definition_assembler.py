"""
Definition assembler for constructing definitional responses.

This module implements the assembler that takes retrieved RFC sections and
constructs coherent definitional responses with proper citations.
"""

import logging
from typing import Dict, List, Optional, Tuple

from ..contracts.models import Query, QueryResponse, QueryType, RFCSection
from ..contracts.settings import settings

logger = logging.getLogger(__name__)


class DefinitionAssembler:
    """Assembles definitional responses from retrieved RFC sections."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.assembler")
        self.strict_mode = settings.strict_definitions
        
        # Definition quality indicators
        self.definition_indicators = [
            "is defined as",
            "means",
            "refers to",
            "denotes",
            "represents",
            "specifies",
            "defines",
            "describes",
        ]
        
        self.logger.info(f"Definition assembler initialized (strict_mode: {self.strict_mode})")
    
    def assemble_definition(
        self,
        query: Query,
        retrieved_sections: List[Tuple[RFCSection, float]],
        query_id: str
    ) -> QueryResponse:
        """Assemble a definitional response from retrieved sections."""
        start_time = self._get_current_time_ms()
        
        if not retrieved_sections:
            return self._create_empty_response(query, query_id, start_time)
        
        # Filter and rank sections for definition quality
        definition_sections = self._filter_definition_sections(retrieved_sections)
        
        if not definition_sections and self.strict_mode:
            return self._create_strict_mode_failure_response(query, query_id, start_time)
        
        # Select the best definition section
        best_section, confidence = self._select_best_definition(definition_sections or retrieved_sections)
        
        # Construct the response
        response_content = self._construct_definition_content(best_section, confidence)
        citations = self._extract_citations([best_section])
        
        processing_time = self._get_current_time_ms() - start_time
        
        response = QueryResponse(
            query_id=query_id,
            response_type=QueryType.DEFINITION,
            content=response_content,
            citations=citations,
            confidence=confidence,
            processing_time_ms=processing_time
        )
        
        self.logger.info(
            f"Assembled definition response for '{query.text}' "
            f"(confidence: {confidence:.2f}, time: {processing_time}ms)"
        )
        
        return response
    
    def _filter_definition_sections(
        self,
        sections: List[Tuple[RFCSection, float]]
    ) -> List[Tuple[RFCSection, float]]:
        """Filter sections that contain actual definitions."""
        definition_sections = []
        
        for section, score in sections:
            if self._contains_definition(section.excerpt):
                # Boost score for definition-containing sections
                boosted_score = min(score * 1.2, 1.0)
                definition_sections.append((section, boosted_score))
        
        # Sort by boosted score
        definition_sections.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.debug(f"Filtered {len(definition_sections)} definition sections from {len(sections)} total")
        return definition_sections
    
    def _contains_definition(self, text: str) -> bool:
        """Check if text contains a definition."""
        text_lower = text.lower()
        
        # Check for definition indicators
        for indicator in self.definition_indicators:
            if indicator in text_lower:
                return True
        
        # Check for formal definition patterns
        definition_patterns = [
            r"(\w+)\s+is\s+defined\s+as",
            r"(\w+)\s+means",
            r"(\w+)\s+refers\s+to",
            r"(\w+)\s+denotes",
        ]
        
        import re
        for pattern in definition_patterns:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def _select_best_definition(
        self,
        sections: List[Tuple[RFCSection, float]]
    ) -> Tuple[RFCSection, float]:
        """Select the best definition section based on quality and relevance."""
        if not sections:
            raise ValueError("No sections provided for definition selection")
        
        # For now, return the highest scoring section
        # In the future, this could implement more sophisticated selection logic
        best_section, best_score = sections[0]
        
        # Additional quality checks
        if self._is_high_quality_definition(best_section):
            best_score = min(best_score * 1.1, 1.0)
        
        return best_section, best_score
    
    def _is_high_quality_definition(self, section: RFCSection) -> bool:
        """Check if a section contains a high-quality definition."""
        text = section.excerpt.lower()
        
        # Check for multiple quality indicators
        quality_indicators = 0
        
        # Formal definition patterns
        if any(indicator in text for indicator in self.definition_indicators):
            quality_indicators += 1
        
        # RFC section number indicates formal definition
        if section.section in ["1", "1.1", "2", "2.1", "3", "3.1"]:
            quality_indicators += 1
        
        # Contains technical details
        technical_terms = ["protocol", "packet", "header", "field", "bit", "byte"]
        if any(term in text for term in technical_terms):
            quality_indicators += 1
        
        # Reasonable length (not too short, not too long)
        if 50 <= len(section.excerpt) <= 500:
            quality_indicators += 1
        
        return quality_indicators >= 2
    
    def _construct_definition_content(
        self,
        section: RFCSection,
        confidence: float
    ) -> Dict[str, any]:
        """Construct the response content from a definition section."""
        # Extract the most relevant part of the excerpt
        definition_text = self._extract_definition_text(section.excerpt)
        
        content = {
            "definition": definition_text,
            "source": {
                "rfc_number": section.rfc_number,
                "section": section.section,
                "title": section.title,
                "url": section.url,
            },
            "confidence": confidence,
            "strict_mode": self.strict_mode,
        }
        
        return content
    
    def _extract_definition_text(self, excerpt: str) -> str:
        """Extract the most relevant definition text from an excerpt."""
        # For now, return the first sentence or first 200 characters
        # In the future, this could implement more sophisticated extraction
        
        # Try to find the first sentence
        sentences = excerpt.split('.')
        if sentences and sentences[0].strip():
            first_sentence = sentences[0].strip()
            if len(first_sentence) > 20:  # Ensure it's substantial
                return first_sentence + "."
        
        # Fallback to first 200 characters
        return excerpt[:200].strip()
    
    def _extract_citations(self, sections: List[RFCSection]) -> List[str]:
        """Extract citations from sections."""
        citations = []
        
        for section in sections:
            citation = f"RFC {section.rfc_number}, Section {section.section}: {section.title}"
            citations.append(citation)
        
        return citations
    
    def _create_empty_response(
        self,
        query: Query,
        query_id: str,
        start_time: float
    ) -> QueryResponse:
        """Create an empty response when no relevant sections are found."""
        processing_time = self._get_current_time_ms() - start_time
        
        return QueryResponse(
            query_id=query_id,
            response_type=QueryType.DEFINITION,
            content={
                "definition": "No definition found for the requested term.",
                "source": None,
                "confidence": 0.0,
                "strict_mode": self.strict_mode,
            },
            citations=[],
            confidence=0.0,
            processing_time_ms=processing_time
        )
    
    def _create_strict_mode_failure_response(
        self,
        query: Query,
        query_id: str,
        start_time: float
    ) -> QueryResponse:
        """Create a response indicating strict mode failure."""
        processing_time = self._get_current_time_ms() - start_time
        
        return QueryResponse(
            query_id=query_id,
            response_type=QueryType.DEFINITION,
            content={
                "definition": "No formal definition found. Strict mode requires explicit definitions from RFC documents.",
                "source": None,
                "confidence": 0.0,
                "strict_mode": self.strict_mode,
                "strict_mode_failure": True,
            },
            citations=[],
            confidence=0.0,
            processing_time_ms=processing_time
        )
    
    def _get_current_time_ms(self) -> float:
        """Get current time in milliseconds."""
        import time
        return time.time() * 1000
    
    def get_assembler_stats(self) -> Dict[str, any]:
        """Get statistics about the assembler."""
        return {
            "strict_mode": self.strict_mode,
            "definition_indicators": len(self.definition_indicators),
            "quality_threshold": 2,  # Minimum quality indicators for high-quality definition
        } 