"""
Prometheus metrics for AE v2 observability.

This module defines and manages Prometheus metrics for
monitoring AE v2 performance and behavior.
"""

from prometheus_client import Counter, Histogram

# HTTP request metrics
REQUEST_LATENCY = Histogram(
    "ae_http_request_latency_ms",
    "HTTP request latency in milliseconds",
    ["route", "method", "status"],
)

# Query processing metrics
QUERY_LATENCY = Histogram(
    "ae_query_latency_ms",
    "Query processing latency in milliseconds",
    ["intent", "mode"],
)

# Router decision metrics
ROUTER_INTENT = Counter(
    "ae_router_intent_total", "Total router intent decisions", ["intent"]
)

ROUTER_TARGET = Counter(
    "ae_router_target_total", "Total router target selections", ["kind", "name"]
)

# Cache performance metrics
CACHE_HIT = Counter("ae_cache_hits_total", "Total cache hits", ["scope"])

CACHE_MISS = Counter("ae_cache_misses_total", "Total cache misses", ["scope"])

# Search performance metrics
SEARCH_LATENCY = Histogram(
    "ae_search_latency_ms", "Search operation latency in milliseconds", ["mode"]
)

# Concept compilation metrics
CONCEPT_COMPILE_LATENCY = Histogram(
    "ae_concept_compile_latency_ms",
    "Concept compilation latency in milliseconds",
    ["slug"],
)

CONCEPT_COMPILE_SUCCESS = Counter(
    "ae_concept_compile_success_total",
    "Total successful concept compilations",
    ["slug"],
)

CONCEPT_COMPILE_FAILURE = Counter(
    "ae_concept_compile_failure_total",
    "Total failed concept compilations",
    ["slug", "error_type"],
)

# Playbook execution metrics
PLAYBOOK_LATENCY = Histogram(
    "ae_playbook_latency_ms", "Playbook execution latency in milliseconds", ["slug"]
)

PLAYBOOK_SUCCESS = Counter(
    "ae_playbook_success_total", "Total successful playbook executions", ["slug"]
)

PLAYBOOK_FAILURE = Counter(
    "ae_playbook_failure_total",
    "Total failed playbook executions",
    ["slug", "error_type"],
)


def record_request_latency(
    route: str, method: str, status: int, latency_ms: float
) -> None:
    """Record HTTP request latency."""
    REQUEST_LATENCY.labels(route=route, method=method, status=str(status)).observe(
        latency_ms
    )


def record_query_latency(intent: str, mode: str, latency_ms: float) -> None:
    """Record query processing latency."""
    QUERY_LATENCY.labels(intent=intent, mode=mode).observe(latency_ms)


def record_router_intent(intent: str) -> None:
    """Record router intent decision."""
    ROUTER_INTENT.labels(intent=intent).inc()


def record_router_target(kind: str, name: str) -> None:
    """Record router target selection."""
    ROUTER_TARGET.labels(kind=kind, name=name).inc()


def record_cache_hit(scope: str) -> None:
    """Record cache hit."""
    CACHE_HIT.labels(scope=scope).inc()


def record_cache_miss(scope: str) -> None:
    """Record cache miss."""
    CACHE_MISS.labels(scope=scope).inc()


def record_search_latency(mode: str, latency_ms: float) -> None:
    """Record search operation latency."""
    SEARCH_LATENCY.labels(mode=mode).observe(latency_ms)


def record_concept_compile_latency(slug: str, latency_ms: float) -> None:
    """Record concept compilation latency."""
    CONCEPT_COMPILE_LATENCY.labels(slug=slug).observe(latency_ms)


def record_concept_compile_success(slug: str) -> None:
    """Record successful concept compilation."""
    CONCEPT_COMPILE_SUCCESS.labels(slug=slug).inc()


def record_concept_compile_failure(slug: str, error_type: str) -> None:
    """Record failed concept compilation."""
    CONCEPT_COMPILE_FAILURE.labels(slug=slug, error_type=error_type).inc()


def record_playbook_latency(slug: str, latency_ms: float) -> None:
    """Record playbook execution latency."""
    PLAYBOOK_LATENCY.labels(slug=slug).observe(latency_ms)


def record_playbook_success(slug: str) -> None:
    """Record successful playbook execution."""
    PLAYBOOK_SUCCESS.labels(slug=slug).inc()


def record_playbook_failure(slug: str, error_type: str) -> None:
    """Record failed playbook execution."""
    PLAYBOOK_FAILURE.labels(slug=slug, error_type=error_type).inc()
