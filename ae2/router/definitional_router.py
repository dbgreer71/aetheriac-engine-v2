from __future__ import annotations
from dataclasses import dataclass
from typing import List
from ae2.contracts.models import Query
from ae2.router.lexicon import LEXICON  # dict with "protocol_terms"


@dataclass
class Route:
    intent: str
    normalized_terms: List[str]


class DefinitionalRouter:
    def route_query(self, q: Query) -> Route:
        text = (q.text or "").lower()
        proto_terms = set(LEXICON.get("protocol_terms", []))
        terms = sorted({t for t in proto_terms if t in text})
        return Route(intent="DEFINE", normalized_terms=terms)
