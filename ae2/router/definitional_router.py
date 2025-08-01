"""
Definitional router for query classification and routing.

This module implements a router that classifies queries and routes them to
appropriate handlers based on their intent and content.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from ..contracts.models import Query, QueryType
from ..contracts.settings import settings

logger = logging.getLogger(__name__)


class DefinitionalRouter:
    """Routes queries to appropriate handlers based on intent classification."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.router")
        
        # Define keyword patterns for different query types
        self.definition_patterns = {
            "what_is": [
                r"what\s+is\s+(\w+)",
                r"define\s+(\w+)",
                r"definition\s+of\s+(\w+)",
                r"meaning\s+of\s+(\w+)",
                r"explain\s+(\w+)",
            ],
            "how_does": [
                r"how\s+does\s+(\w+)\s+work",
                r"how\s+(\w+)\s+works",
                r"explain\s+how\s+(\w+)",
            ],
            "protocol_terms": [
                r"\b(arp|ospf|bgp|tcp|udp|ipv4|ipv6|mpls|dhcp|dns)\b",
            ]
        }
        
        self.concept_patterns = {
            "compare": [
                r"compare\s+(\w+)\s+and\s+(\w+)",
                r"difference\s+between\s+(\w+)\s+and\s+(\w+)",
                r"(\w+)\s+vs\s+(\w+)",
            ],
            "relationship": [
                r"relationship\s+between\s+(\w+)\s+and\s+(\w+)",
                r"how\s+(\w+)\s+relates\s+to\s+(\w+)",
            ],
            "examples": [
                r"examples?\s+of\s+(\w+)",
                r"(\w+)\s+examples?",
                r"show\s+me\s+(\w+)",
            ]
        }
        
        self.troubleshooting_patterns = {
            "problem": [
                r"problem\s+with\s+(\w+)",
                r"(\w+)\s+not\s+working",
                r"(\w+)\s+error",
                r"(\w+)\s+failure",
                r"(\w+)\s+down",
            ],
            "fix": [
                r"how\s+to\s+fix\s+(\w+)",
                r"troubleshoot\s+(\w+)",
                r"resolve\s+(\w+)\s+issue",
                r"(\w+)\s+configuration",
            ],
            "debug": [
                r"debug\s+(\w+)",
                r"diagnose\s+(\w+)",
                r"(\w+)\s+logs?",
                r"(\w+)\s+status",
            ]
        }
        
        # Build compiled regex patterns
        self._compile_patterns()
        
        # Network protocol lexicon
        self.protocol_lexicon = {
            "routing": ["ospf", "bgp", "rip", "eigrp", "isis"],
            "switching": ["stp", "rstp", "mstp", "vlan", "trunk"],
            "addressing": ["arp", "dhcp", "dns", "nat", "pat"],
            "transport": ["tcp", "udp", "sctp"],
            "network": ["ipv4", "ipv6", "mpls", "vpn", "gre"],
            "security": ["acl", "firewall", "vpn", "ipsec", "ssl"],
        }
        
        self.logger.info("Definitional router initialized")
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        self.compiled_definition_patterns = {}
        for category, patterns in self.definition_patterns.items():
            self.compiled_definition_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        self.compiled_concept_patterns = {}
        for category, patterns in self.concept_patterns.items():
            self.compiled_concept_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        self.compiled_troubleshooting_patterns = {}
        for category, patterns in self.troubleshooting_patterns.items():
            self.compiled_troubleshooting_patterns[category] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def classify_query(self, query_text: str) -> Tuple[QueryType, float, Dict[str, any]]:
        """Classify a query and return its type with confidence score."""
        query_text_lower = query_text.lower().strip()
        
        # Calculate scores for each query type
        definition_score = self._calculate_definition_score(query_text_lower)
        concept_score = self._calculate_concept_score(query_text_lower)
        troubleshooting_score = self._calculate_troubleshooting_score(query_text_lower)
        
        # Determine the highest scoring type
        scores = {
            QueryType.DEFINITION: definition_score,
            QueryType.CONCEPT: concept_score,
            QueryType.TROUBLESHOOTING: troubleshooting_score,
        }
        
        best_type = max(scores, key=scores.get)
        confidence = scores[best_type]
        
        # Extract additional context
        context = self._extract_context(query_text_lower, best_type)
        
        self.logger.debug(
            f"Query classified as {best_type} with confidence {confidence:.2f}: {query_text}"
        )
        
        return best_type, confidence, context
    
    def _calculate_definition_score(self, query_text: str) -> float:
        """Calculate score for definition queries."""
        score = 0.0
        
        # Check definition patterns
        for category, patterns in self.compiled_definition_patterns.items():
            for pattern in patterns:
                if pattern.search(query_text):
                    if category == "what_is":
                        score += 0.8
                    elif category == "how_does":
                        score += 0.6
                    elif category == "protocol_terms":
                        score += 0.4
        
        # Check for protocol terms
        protocol_terms = self._extract_protocol_terms(query_text)
        if protocol_terms:
            score += 0.3 * len(protocol_terms)
        
        # Check for question words
        question_words = ["what", "define", "definition", "meaning", "explain"]
        if any(word in query_text for word in question_words):
            score += 0.2
        
        return min(score, 1.0)
    
    def _calculate_concept_score(self, query_text: str) -> float:
        """Calculate score for concept queries."""
        score = 0.0
        
        # Check concept patterns
        for category, patterns in self.compiled_concept_patterns.items():
            for pattern in patterns:
                if pattern.search(query_text):
                    if category == "compare":
                        score += 0.8
                    elif category == "relationship":
                        score += 0.7
                    elif category == "examples":
                        score += 0.6
        
        # Check for comparison words
        comparison_words = ["compare", "difference", "vs", "versus", "relationship"]
        if any(word in query_text for word in comparison_words):
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_troubleshooting_score(self, query_text: str) -> float:
        """Calculate score for troubleshooting queries."""
        score = 0.0
        
        # Check troubleshooting patterns
        for category, patterns in self.compiled_troubleshooting_patterns.items():
            for pattern in patterns:
                if pattern.search(query_text):
                    if category == "problem":
                        score += 0.8
                    elif category == "fix":
                        score += 0.7
                    elif category == "debug":
                        score += 0.6
        
        # Check for problem words
        problem_words = ["problem", "error", "failure", "down", "not working", "fix", "troubleshoot"]
        if any(word in query_text for word in problem_words):
            score += 0.4
        
        return min(score, 1.0)
    
    def _extract_protocol_terms(self, query_text: str) -> Set[str]:
        """Extract protocol terms from query text."""
        terms = set()
        
        # Flatten protocol lexicon
        all_protocols = []
        for protocols in self.protocol_lexicon.values():
            all_protocols.extend(protocols)
        
        # Find matches
        for protocol in all_protocols:
            if protocol in query_text:
                terms.add(protocol)
        
        return terms
    
    def _extract_context(self, query_text: str, query_type: QueryType) -> Dict[str, any]:
        """Extract additional context from the query."""
        context = {
            "protocol_terms": list(self._extract_protocol_terms(query_text)),
            "query_length": len(query_text),
        }
        
        if query_type == QueryType.DEFINITION:
            # Extract the term being defined
            for pattern in self.compiled_definition_patterns["what_is"]:
                match = pattern.search(query_text)
                if match:
                    context["target_term"] = match.group(1)
                    break
        
        elif query_type == QueryType.CONCEPT:
            # Extract terms being compared
            for pattern in self.compiled_concept_patterns["compare"]:
                match = pattern.search(query_text)
                if match:
                    context["compare_terms"] = [match.group(1), match.group(2)]
                    break
        
        elif query_type == QueryType.TROUBLESHOOTING:
            # Extract the problematic component
            for pattern in self.compiled_troubleshooting_patterns["problem"]:
                match = pattern.search(query_text)
                if match:
                    context["problematic_component"] = match.group(1)
                    break
        
        return context
    
    def route_query(self, query: Query) -> Dict[str, any]:
        """Route a query to the appropriate handler."""
        query_type, confidence, context = self.classify_query(query.text)
        
        # Update query with classified type
        query.query_type = query_type
        
        routing_info = {
            "query_type": query_type,
            "confidence": confidence,
            "context": context,
            "handler": self._get_handler_for_type(query_type),
            "requires_strict_mode": self._requires_strict_mode(query_type, context),
        }
        
        self.logger.info(
            f"Routed query '{query.text}' to {query_type} handler "
            f"(confidence: {confidence:.2f})"
        )
        
        return routing_info
    
    def _get_handler_for_type(self, query_type: QueryType) -> str:
        """Get the handler name for a query type."""
        handlers = {
            QueryType.DEFINITION: "definition_assembler",
            QueryType.CONCEPT: "concept_assembler",
            QueryType.TROUBLESHOOTING: "troubleshooting_assembler",
        }
        return handlers.get(query_type, "default_assembler")
    
    def _requires_strict_mode(self, query_type: QueryType, context: Dict[str, any]) -> bool:
        """Determine if strict mode is required for this query."""
        if not settings.strict_definitions:
            return False
        
        # Always use strict mode for definition queries
        if query_type == QueryType.DEFINITION:
            return True
        
        # Use strict mode for concept queries with protocol terms
        if query_type == QueryType.CONCEPT and context.get("protocol_terms"):
            return True
        
        return False
    
    def get_router_stats(self) -> Dict[str, any]:
        """Get statistics about the router."""
        return {
            "definition_patterns": len(self.definition_patterns),
            "concept_patterns": len(self.concept_patterns),
            "troubleshooting_patterns": len(self.troubleshooting_patterns),
            "protocol_lexicon_size": sum(len(protocols) for protocols in self.protocol_lexicon.values()),
            "strict_definitions_enabled": settings.strict_definitions,
        } 