"""
Definition assembler for RFC-based answers.

This module assembles definitional responses by finding the best RFC section
for a given target RFC number, with bias toward introduction/overview sections.
"""

from typing import Dict, Any
from ..retriever.index_store import IndexStore


def assemble_definition(
    target_rfc: str, query: str, store: IndexStore, mode: str = "hybrid"
) -> Dict[str, Any]:
    """
    Assemble a definitional response from RFC sections.

    Args:
        target_rfc: RFC number as string
        query: Original user query
        store: IndexStore for searching
        mode: Search mode (hybrid, tfidf, bm25)

    Returns:
        Dictionary with answer, citations, and metadata
    """
    try:
        rfc_num = int(target_rfc)
    except ValueError:
        # Fallback to OSPF if invalid RFC number
        rfc_num = 2328

    # Search for relevant sections in the target RFC
    # Bias toward introduction/overview sections
    search_terms = query.split()

    # Add RFC-specific terms for better targeting
    if rfc_num == 2328:  # OSPF
        search_terms.extend(["ospf", "open shortest path first", "routing protocol"])
    elif rfc_num == 826:  # ARP
        search_terms.extend(["arp", "address resolution protocol", "mac address"])
    elif rfc_num == 4271:  # BGP
        search_terms.extend(["bgp", "border gateway protocol", "autonomous system"])
    elif rfc_num == 9293:  # TCP
        search_terms.extend(["tcp", "transmission control protocol", "reliable"])
    elif rfc_num == 791:  # IP
        search_terms.extend(["ip", "internet protocol", "datagram"])

    # Create search query
    search_query = " ".join(search_terms)

    # Search with RFC filter and bias toward intro sections
    hits = store.search(search_query, top_k=5, rfc_filter=[rfc_num], mode=mode)

    if not hits:
        # Fallback: search without RFC filter
        hits = store.search(search_query, top_k=3, mode=mode)

    if not hits:
        return {
            "answer": f"No relevant sections found for RFC {rfc_num}.",
            "citations": [],
            "confidence": 0.0,
            "source_rfc": rfc_num,
        }

    # Select best hit (prioritize introduction/overview sections)
    best_hit = hits[0]

    # Check if it's an introduction section
    section = best_hit.get("section", "")
    title = best_hit.get("title", "").lower()

    # Bias toward introduction/overview sections
    intro_keywords = [
        "introduction",
        "overview",
        "1.",
        "1.1",
        "terminology",
        "definitions",
    ]
    is_intro = any(keyword in title or keyword in section for keyword in intro_keywords)

    # If not intro, try to find one in top hits
    if not is_intro and len(hits) > 1:
        for hit in hits[1:]:
            hit_title = hit.get("title", "").lower()
            hit_section = hit.get("section", "")
            if any(
                keyword in hit_title or keyword in hit_section
                for keyword in intro_keywords
            ):
                best_hit = hit
                break

    # Extract answer text
    excerpt = best_hit.get("excerpt", best_hit.get("title", ""))
    if len(excerpt) > 800:
        excerpt = excerpt[:800] + "..."

    # Create citation
    citation = {
        "rfc": best_hit.get("rfc", rfc_num),
        "section": best_hit.get("section", ""),
        "title": best_hit.get("title", ""),
        "url": best_hit.get("url", f"https://tools.ietf.org/html/rfc{rfc_num}"),
    }

    return {
        "answer": excerpt,
        "citations": [citation],
        "confidence": best_hit.get("score", 0.5),
        "source_rfc": rfc_num,
        "section": best_hit.get("section", ""),
        "title": best_hit.get("title", ""),
    }
