# Aetheriac Engine v2

![CI / test-api](https://github.com/dbgreer71/aetheriac-engine-v2/actions/workflows/ci.yml/badge.svg?job=test-api)
![Full CI](https://github.com/dbgreer71/aetheriac-engine-v2/actions/workflows/ci.yml/badge.svg?job=ci-full)

A clean-slate implementation of the Aetheriac Engine with contract-first design, content-addressed storage, and modular architecture for network knowledge retrieval.

## Quick Start

```bash
# Clone and run first-run demo
git clone <repository-url>
cd aetheriac-engine-v2
make demo
```

The demo runs 6 curated queries (2 define, 2 concept, 2 troubleshoot) and prints `DEMO: PASS` if all evaluations meet expert-level thresholds.

## Overview

AE v2 is a complete rewrite of the Aetheriac Engine with the following key improvements:

- **Contract-first design**: All data structures are defined as Pydantic models with validation
- **Content-addressed storage**: SHA256 hashes ensure data integrity and deduplication
- **Modular architecture**: Clear separation of concerns with independent packages
- **Scientific rigor**: Comprehensive testing, manifests, and traceable provenance
- **Performance**: Hybrid dense/sparse retrieval with sub-500ms response times
- **Hybrid reranker**: BM25 + TF-IDF scoring with configurable weights and debug subscores

## Architecture

### Core Components

- **Contracts** (`ae2/contracts/`): Pydantic models defining all data structures
- **RFC Intake** (`ae2/rfc/`): Downloads and sectionizes RFC documents
- **Retriever** (`ae2/retriever/`): Hybrid dense/sparse search with BM25 + TF-IDF + embeddings
- **Router** (`ae2/router/`): Query classification and routing
- **Assembler** (`ae2/assembler/`): Response construction from retrieved content
- **API** (`ae2/api/`): FastAPI application with health checks and debug endpoints
- **Storage** (`ae2/storage/`): Index management and content-addressed storage

### Data Flow

1. **RFC Sync**: Downloads RFC documents and sectionizes them into searchable chunks
2. **Index Building**: Creates hybrid indexes (dense embeddings + BM25 sparse + TF-IDF)
3. **Query Processing**:
   - Router classifies query intent
   - Retriever finds relevant sections using configurable ranking modes
   - Assembler constructs coherent response
4. **Response**: Returns structured response with citations and confidence scores

## Installation

### From Wheel

```bash
# Install from PyPI (when available)
pip install ae2

# Or install from GitHub release
pip install https://github.com/dbgreer71/aetheriac-engine-v2/releases/download/v0.4.0/ae2-0.4.0-py3-none-any.whl
```

### From Source

```bash
# Clone the repository
git clone https://github.com/dbgreer71/aetheriac-engine-v2.git
cd aetheriac-engine-v2

# Install in development mode
pip install -e .

# Or install with test dependencies
pip install -e ".[test]"
```

### Prerequisites

- Python 3.10+
- 4GB+ RAM (for embedding models)
- 2GB+ disk space

### Configuration

Key environment variables:

```bash
# API settings
AE_BIND_PORT=8000
API_HOST=0.0.0.0

# Index and data directories
AE_INDEX_DIR=data/index
DATA_DIR=data

# Feature flags
ENABLE_DENSE=1
ENABLE_RFC=true
STRICT_DEFINITIONS=true
ENABLE_PLAYBOOKS=false

# Hybrid reranker weights (default: 60% TF-IDF, 40% BM25)
HYBRID_W_TFIDF=0.6
HYBRID_W_BM25=0.4

# Model settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Usage

### Run with Docker

```bash
# Pull from GitHub Container Registry
docker pull ghcr.io/dbgreer71/aetheriac-engine-v2:latest

# Run with default configuration
docker run -d \
  --name aev2 \
  -p 8001:8001 \
  -e AE_BIND_PORT=8001 \
  -e ENABLE_DENSE=0 \
  ghcr.io/dbgreer71/aetheriac-engine-v2:latest

# Or run with custom configuration
docker run -d \
  --name aev2 \
  -p 8001:8001 \
  -v $(pwd)/data:/app/data \
  -e AE_INDEX_DIR=/app/data/index \
  -e AE_BIND_PORT=8001 \
  -e ENABLE_DENSE=0 \
  ghcr.io/dbgreer71/aetheriac-engine-v2:latest
```

### Starting the API

```bash
# Start the API server
python -m ae2.api.main

# Or with custom configuration
AE_INDEX_DIR="$(pwd)/data/index" AE_BIND_PORT=8001 ENABLE_DENSE=0 \
python -m ae2.api.main
```

The API will be available at `http://localhost:8001` (or configured port)

### API Endpoints

#### Query Endpoint

```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What is ARP?",
    "query_type": "definition"
  }'
```

Response:
```json
{
  "query_id": "query_1234567890",
  "response_type": "definition",
  "content": {
    "definition": "ARP (Address Resolution Protocol) is defined as...",
    "source": {
      "rfc_number": 826,
      "section": "1",
      "title": "Introduction",
      "url": "https://www.rfc-editor.org/rfc/rfc826.xml#section-1"
    },
    "confidence": 0.85,
    "strict_mode": true
  },
  "citations": ["RFC 826, Section 1: Introduction"],
  "confidence": 0.85,
  "processing_time_ms": 245.6,
  "created_at": "2024-01-01T12:00:00Z"
}
```

#### Hybrid Reranker (BM25 + TF-IDF)

The API supports three ranking modes via the `mode` parameter:

- `tfidf`: Traditional TF-IDF scoring
- `bm25`: BM25 probabilistic scoring
- `hybrid`: Weighted combination of both (default)

**Debug Explain Endpoint:**
```bash
curl "http://localhost:8000/debug/explain?query=what%20is%20ospf&mode=hybrid"
```

Response with subscores:
```json
{
  "router_decision": {
    "target_rfcs": [2328],
    "mode": "hybrid"
  },
  "top_hits": [
    {
      "rfc": 2328,
      "section": "1.1",
      "title": "1.1. Protocol overview",
      "score": 0.4342315322622336,
      "scores": {
        "tfidf": 0.04043485395128395,
        "bm25": 0.524926549728658,
        "hybrid": 0.2342315322622336
      }
    }
  ]
}
```

**Query Endpoint with Mode:**
```bash
curl -X POST "http://localhost:8000/query?mode=hybrid" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is ARP?","top_k":3}'
```

Response with debug scores:
```json
{
  "answer": "RFC 826",
  "citations": [

### Troubleshooting Playbooks (v1)

The playbook system provides deterministic troubleshooting workflows with vendor-specific commands and RFC citations.

#### Execute OSPF Neighbor-Down Playbook
```bash
curl -X POST "http://localhost:8001/troubleshoot/ospf-neighbor" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "iosxe",
    "iface": "GigabitEthernet0/0",
    "area": "0.0.0.0",
    "auth": "md5",
    "mtu": 1500
  }'
```

#### Execute BGP Neighbor-Down Playbook

**IOS-XE Example:**
```bash
curl -X POST "http://localhost:8001/troubleshoot/bgp-neighbor" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "iosxe",
    "peer": "192.0.2.1",
    "iface": "GigabitEthernet0/0",
    "ttl": 1,
    "multihop": false
  }'
```

**Junos Example:**
```bash
curl -X POST "http://localhost:8001/troubleshoot/bgp-neighbor" \
  -H "Content-Type: application/json" \
  -d '{
    "vendor": "junos",
    "peer": "192.0.2.1",
    "iface": "ge-0/0/0",
    "ttl": 1,
    "multihop": true
  }'
```

Returns an ordered list of 10 deterministic troubleshooting steps with vendor-specific commands:

```json
{
  "playbook_id": "bgp-neighbor-down",
  "steps": [
    {
      "rule_id": "check_neighbor_fsm_state",
      "check": "Check BGP neighbor FSM state (Idle/Active/Connect/OpenSent/OpenConfirm/Established)",
      "result": "Check BGP neighbor FSM state for 192.0.2.1 using vendor-specific commands",
      "fix": null,
      "verify": "Neighbor should be in Established state",
      "commands": ["show ip bgp summary", "show ip bgp neighbors 192.0.2.1"],
      "citations": [
        {
          "rfc": 4271,
          "section": "8",
          "title": "BGP Finite State Machine",
          "url": "https://tools.ietf.org/html/rfc4271#section-8"
        }
      ]
    },
    {
      "rule_id": "check_tcp_179_reachability",
      "check": "Verify TCP connectivity to port 179 and source interface",
      "result": "Verify TCP connectivity to 192.0.2.1 on port 179",
      "fix": "Check network connectivity and routing to peer",
      "verify": "TCP connection to port 179 should be established",
      "commands": ["show ip bgp neighbors 192.0.2.1", "show control-plane host open-ports"],
      "citations": [
        {
          "rfc": 4271,
          "section": "6.8",
          "title": "TCP Connection",
          "url": "https://tools.ietf.org/html/rfc4271#section-6.8"
        }
      ]
    }
  ],
  "debug": {
    "matched_rules": 10,
    "vendor": "iosxe",
    "peer": "192.0.2.1",
    "iface": "GigabitEthernet0/0"
  }
}
```

#### Explain Playbook
```bash
curl "http://localhost:8001/debug/explain_playbook?slug=bgp-neighbor-down&vendor=iosxe"
```

Returns playbook structure with rule conditions and command mappings.

#### Supported Vendors
- **IOS-XE**: Cisco IOS-XE commands (e.g., `show ip bgp neighbors`)
- **Junos**: Juniper Junos commands (e.g., `show bgp neighbor`)

#### Guardrails
- **Read-only**: All commands are show commands only
- **RFC citations**: Each step includes relevant RFC references
- **Deterministic**: Same context produces identical results
- **Vendor-specific**: Commands rendered for target vendor

### Unified Router & Assembler (v2)

The unified router automatically chooses between Definition, Concept Card, or Troubleshooting paths based on query analysis.

#### Auto Mode Query
```bash
curl -X POST "http://localhost:8000/query?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "what is ospf"
  }'
```

Returns intent and route information:
```json
{
  "intent": "DEFINE",
  "route": {
    "target": "2328",
    "evidence": {
      "matched_terms": ["ospf"],
      "confidence": 0.6,
      "notes": "Definition query for RFC 2328"
    }
  },
  "answer": "OSPF (Open Shortest Path First) is a link-state routing protocol...",
  "citations": [...],
  "confidence": 0.7,
  "mode": "auto"
}
```

#### Concept Card Query
```bash
curl -X POST "http://localhost:8000/query?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "arp concept card"
  }'
```

#### Troubleshooting Query
```bash
curl -X POST "http://localhost:8000/query?mode=auto" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ospf neighbor down on iosxe g0/0",
    "vendor": "iosxe",
    "iface": "GigabitEthernet0/0",
    "area": "0.0.0.0"
  }'
```

#### Debug Route Endpoint
```bash
curl "http://localhost:8000/debug/route?query=what%20is%20ospf"
```

Returns routing decision without assembly:
```json
{
  "query": "what is ospf",
  "intent": "DEFINE",
  "target": "2328",
  "confidence": 0.6,
  "matches": ["ospf"],
  "notes": "Definition query for RFC 2328",
  "mode_used": "hybrid"
}
```

#### Intent Detection
- **TROUBLESHOOT**: Contains troubleshooting keywords + protocol + vendor
- **CONCEPT**: Contains concept keywords or exact concept slug match
- **DEFINE**: Default fallback for definitional queries

#### Supported Modes
- `auto`: Intelligent routing (new)
- `hybrid`: BM25 + TF-IDF combination (existing)
- `tfidf`: Traditional TF-IDF scoring (existing)
- `bm25`: BM25 probabilistic scoring (existing)

#### Guardrails
- **Deterministic**: Same query produces identical routing
- **Fallback**: Concept requests fall back to definition if card missing
- **Vendor validation**: Only supported vendors (iosxe, junos) for troubleshooting
- **Timeout**: 150ms assembly timeout enforced
    {
      "citation_text": "RFC 826 §1 — RFC 826",
      "url": "https://www.rfc-editor.org/rfc/rfc826.txt"
    }
  ],
  "mode": "hybrid",
  "debug": {
    "score": 0.23111070354699204,
    "scores": {
      "tfidf": 0.018862965789201526,
      "bm25": 0.3494823101836778,
      "hybrid": 0.15111070354699205
    }
  }
}
```

#### Debug Endpoints

```bash
# Health check
curl http://localhost:8000/healthz

# Index statistics
curl http://localhost:8000/debug/index

# Raw search results
curl -X POST "http://localhost:8000/debug/search" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is ARP?"}'
```

### Ranking Sanity Check

Test the hybrid reranker with these commands:

```bash
# Start server
AE_INDEX_DIR="$(pwd)/data/index" AE_BIND_PORT=8001 ENABLE_DENSE=0 \
python -m ae2.api.main &

# Health check
curl -s http://localhost:8001/healthz | jq .

# Test hybrid mode
curl -s "http://localhost:8001/debug/explain?query=what%20is%20ospf&mode=hybrid" | jq .

# Test query endpoint
curl -s -X POST "http://localhost:8001/query?mode=hybrid" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is ARP?","top_k":3}' | jq .
```

Expected results:
- `/healthz` shows correct section count and manifest present
- `/debug/explain?...&mode=hybrid` returns `scores.tfidf`, `scores.bm25`, `scores.hybrid`
- `/query?mode=hybrid` returns clean citations (RFC §, title)

### Troubleshooting

**Server appears hung during startup:**
- Rebuild the index: `python scripts/build_index.py`
- Ensure port 8001 is free: `lsof -i :8001`
- Check index files exist: `ls -la data/index/`

**Missing BM25 tokens:**
- The system will fallback to TF-IDF only if `bm25_tokens.npy` is missing
- Rebuild index to regenerate: `python scripts/build_index.py`

### Concept Cards

Concept Cards provide structured knowledge about network concepts with evidence and provenance. They are automatically compiled from RFC search results and stored with full traceability.

**Compile a Concept Card:**
```bash
curl -X POST "http://localhost:8000/concepts/compile?slug=arp"
```

Response:
```json
{
  "id": "concept:arp:v1",
  "definition": {
    "text": "ARP (Address Resolution Protocol) is defined as...",
    "rfc_number": 826,
    "section": "1",
    "url": "https://www.rfc-editor.org/rfc/rfc826.txt"
  },
  "claims": [
    {
      "text": "ARP maps IP addresses to MAC addresses...",
      "evidence": [
        {
          "type": "rfc",
          "url_or_path": "https://www.rfc-editor.org/rfc/rfc826.txt",
          "sha256": "a1b2c3d4e5f6..."
        }
      ]
    }
  ],
  "provenance": {
    "built_at": "2024-01-01T12:00:00Z"
  }
}
```

**Retrieve a Concept Card:**
```bash
curl "http://localhost:8000/concepts/concept:arp:v1"
```

**Debug Concept Card with Retrieval Trace:**
```bash
curl "http://localhost:8000/debug/concept/concept:arp:v1"
```

**List All Concept Cards:**
```bash
curl "http://localhost:8000/concepts"
```

**Storage Location:**
Concept cards are stored in `data/concepts/` with a manifest file tracking all cards and their SHA256 hashes for integrity verification.

**Retrieval Heuristic:**
The compiler prefers definitional sections (Introduction, Overview, Terminology) and specific RFCs (RFC 826 for ARP, RFC 2328 for OSPF, etc.) when building concept cards.

**Error Handling:**
Concept compilation uses typed error codes for predictable failure handling:

| Error Code | Description |
|------------|-------------|
| `LOW_CONFIDENCE` | Top retrieval score below `CONCEPT_MIN_SCORE` threshold |
| `NO_MATCH` | No search results returned (rare with TF-IDF/BM25) |
| `BAD_CARD` | Concept card assembly or validation failure |
| `MISSING_CITATION` | Required evidence or citation data incomplete |

**Configuration:**
Set `CONCEPT_MIN_SCORE` environment variable to control confidence threshold (default: 0.05).

**Example Error Response:**
```bash
curl -X POST "http://localhost:8000/concepts/compile?slug=xyz123nonexistent"
```

```json
{
  "detail": {
    "error": "concept_compile_error",
    "code": "LOW_CONFIDENCE",
    "message": "No section above min_score=0.05",
    "slug": "xyz123nonexistent"
  }
}
```

**Example Success Response:**
```bash
curl -X POST "http://localhost:8000/concepts/compile?slug=arp"
```

```json
{
  "id": "concept:arp:v1",
  "definition": {
    "text": "ARP (Address Resolution Protocol) is defined as...",
    "rfc_number": 826,
    "section": "1",
    "url": "https://www.rfc-editor.org/rfc/rfc826.txt"
  },
  "claims": [
    {
      "text": "ARP maps IP addresses to MAC addresses...",
      "evidence": [
        {
          "type": "rfc",
          "url_or_path": "https://www.rfc-editor.org/rfc/rfc826.txt",
          "sha256": "a1b2c3d4e5f6..."
        }
      ]
    }
  ],
  "provenance": {
    "built_at": "2024-01-01T12:00:00Z"
  }
}
```

**Persistence and Browsing:**

Compile and save a concept card:
```bash
curl -X POST "http://localhost:8000/concepts/compile?slug=arp&save=true"
```

List all saved concepts:
```bash
curl "http://localhost:8000/concepts/list"
```

Response:
```json
[
  {
    "id": "arp",
    "sha256": "a1b2c3d4e5f6...",
    "bytes": 1234,
    "built_at": "2024-01-01T12:00:00Z",
    "stale": false
  }
]
```

Retrieve a saved concept by slug:
```bash
curl "http://localhost:8000/concepts/arp"
```

**Rebuild and Delete:**

Rebuild a concept card from the current index:
```bash
curl -X POST "http://localhost:8000/concepts/rebuild?slug=arp"
```

Delete a concept card:
```bash
curl -X DELETE "http://localhost:8000/concepts/arp"
```

**JSON Schema:**

Get the JSON schema for concept cards:
```bash
curl "http://localhost:8000/concepts/schema"
```

Response snippet:
```json
{
  "title": "ConceptCard",
  "type": "object",
  "properties": {
    "id": {"type": "string"},
    "definition": {"$ref": "#/$defs/Definition"},
    "claims": {"type": "array", "items": {"$ref": "#/$defs/Claim"}},
    "provenance": {"$ref": "#/$defs/Provenance"}
  }
}
```

**Stale Detection:**

The `stale` flag indicates whether a concept card was compiled from a different index version than the current one. This is computed dynamically and not persisted:

- `stale: false` - Card was compiled from the current index
- `stale: true` - Card was compiled from a different index version

The stale flag is included in both `/concepts/list` and `/concepts/{slug}` responses.

**Evidence Integrity:**

Concept cards now include enhanced evidence fields for better integrity:

```json
{
  "evidence": [
    {
      "type": "rfc",
      "url_or_path": "https://www.rfc-editor.org/rfc/rfc826.txt",
      "sha256": "a1b2c3d4e5f6...",
      "length": 1234,
      "source": {
        "type": "rfc",
        "rfc_number": 826,
        "section": "1",
        "title": "Introduction",
        "url": "https://www.rfc-editor.org/rfc/rfc826.txt"
      }
    }
  ]
}
```

**Deterministic Diff:**

Compare stored and current concept cards:

```bash
# Diff stored vs current (recompiled from live index)
curl "http://localhost:8000/concepts/diff/arp"

# Diff stored vs stored (empty diff)
curl "http://localhost:8000/concepts/diff/arp?recompile=false"
```

Response:
```json
{
  "changed": {"definition": {"text": {"old": "...", "new": "..."}}},
  "added": {},
  "removed": {},
  "provenance": {
    "stored_index": "dcc9f79d...",
    "live_index": "dcc9f79d..."
  }
}
```

**Bulk Compile:**

Compile multiple concepts with bounded concurrency:

```bash
curl -X POST "http://localhost:8000/concepts/compile_many?save=true" \
     -H "Content-Type: application/json" \
     -d '{"slugs": ["arp", "ospf", "tcp"], "mode": "hybrid"}'
```

Response:
```json
{
  "ok": true,
  "results": [
    {
      "slug": "arp",
      "status": "ok",
      "id": "concept:arp:v1",
      "sha256": "a1b2c3d4...",
      "saved": true
    },
    {
      "slug": "bogus",
      "status": "error",
      "error": {
        "code": "LOW_CONFIDENCE",
        "message": "No section above min_score=0.05"
      }
    }
  ],
  "saved_count": 2
}
```

**Export:**

Export concepts to a ZIP file:

```bash
# Export all concepts
curl -X POST "http://localhost:8000/concepts/export" \
     --output concepts_export.zip

# Export specific concepts
curl -X POST "http://localhost:8000/concepts/export" \
     -H "Content-Type: application/json" \
     -d '{"slugs": ["arp", "ospf"]}' \
     --output concepts_export.zip
```

The ZIP contains:
- `concepts_manifest.json` - Current manifest
- `cards/<slug>.json` - Individual concept files (sorted alphabetically)

**Cross-links & Tags:**

Concept cards now support cross-linking and tagging:

```json
{
  "id": "concept:arp:v1",
  "definition": {...},
  "claims": [...],
  "provenance": {...},
  "related": ["ospf", "default-route"],
  "tags": ["arp", "l2", "routing"]
}
```

**Reference Validation:**

Validate cross-links and detect cycles:

```bash
# Validate references for a concept
curl "http://localhost:8000/concepts/validate/arp"
```

Response:
```json
{
  "ok": true,
  "missing": [],
  "cycles": []
}
```

**Pull-through Compilation:**

Automatically compile referenced concepts:

```bash
# Compile arp and pull through its related concepts
curl -X POST "http://localhost:8000/concepts/compile?slug=arp&save=true&pull=true"
```

Response:
```json
{
  "id": "concept:arp:v1",
  "related": ["ospf", "default-route"],
  "pulled": ["ospf"],
  "pulled_errors": []
}
```

**Concept Search:**

Search persisted concept cards:

```bash
# Search for concepts
curl "http://localhost:8000/concepts/search?q=routing&limit=5"
```

Response:
```json
{
  "total": 3,
  "items": [
    {
      "id": "arp",
      "score": 0.85,
      "tags": ["arp", "l2", "routing"],
      "stale": false
    }
  ]
}
```

**Tag Aggregation:**

Get tag usage statistics:

```bash
# Get tag counts
curl "http://localhost:8000/concepts/tags"
```

Response:
```json
{
  "tags": [
    {"tag": "routing", "count": 5},
    {"tag": "arp", "count": 2},
    {"tag": "ospf", "count": 1}
  ]
}
```

**Deterministic Behavior:**

- Cross-links and tags are sorted deterministically when served
- Search results are ranked by TF-IDF score, with ties broken by slug (ascending)
- Tag aggregation is sorted by count (descending), then by tag (ascending)
- Pull-through compilation is limited to depth=1 (no recursion beyond one hop)

### RFC Synchronization

```bash
# Sync RFC documents
python -m ae2.rfc.sync

# Or use the CLI
ae2-sync-rfc
```

### Index Building

```bash
# Build search index
python -m ae2.storage.index_builder

# Or use the CLI
ae2-build-index
```

## Testing

### Running Tests

```bash
# Unit tests
pytest tests/ -v

# Golden tests (comprehensive validation)
pytest tests/ -m golden -v

# Performance tests
pytest tests/ -m slow -v

# All tests with coverage
pytest tests/ --cov=ae2 --cov-report=html
```

### Golden Test Suite

The golden test suite validates core functionality with predefined test cases:

```bash
# Run golden tests directly
python -m ae2.testing.golden_tests
```

Test categories:
- **Definition queries**: "What is ARP?", "Define OSPF"
- **Concept queries**: "Compare ARP and DNS", "Difference between OSPF and BGP"
- **Troubleshooting queries**: "OSPF neighbor down", "BGP not working"

## Evaluation & Gates

### Running Evaluations Locally

```bash
# Build index first
scripts/sync_rfc_min.sh && python scripts/build_index.py

# Run evaluation suites
make eval-defs      # Definition evaluation
make eval-concepts  # Concept card evaluation
make eval-trouble   # Troubleshooting evaluation

# Performance testing
make perf           # 10-repeat performance test
```

### Evaluation Reports

Reports are written to JSON files:
- `eval_defs.json` - Definition accuracy and retrieval metrics
- `eval_concepts.json` - Concept card faithfulness and citation validity
- `eval_trouble.json` - Troubleshooting success and determinism

### Metrics

**Definition Evaluation**:
- `intent_acc`: Query classification accuracy (target: ≥95%)
- `target_acc`: Correct RFC identification (target: ≥92%)
- `p_at_3`: Precision at 3 for retrieval (target: ≥90%)
- `ndcg_at_3`: Normalized DCG at 3 (target: ≥0.92)
- `latency_ms`: Response time percentiles (target: p95 ≤150ms)

**Concept Evaluation**:
- `faithfulness`: All claims have evidence (target: 100%)
- `citation_validity`: Citations include RFC URL + section (target: 100%)
- `latency_ms`: Response time percentiles (target: p95 ≤200ms)

**Troubleshooting Evaluation**:
- `pass_min_steps`: Minimum troubleshooting steps met (target: ≥85%)
- `deterministic`: Identical steps across runs (target: 100%)
- `latency_ms`: Response time percentiles (target: p95 ≤250ms)

**Note**: Current thresholds are staged for plumbing validation. They will be tightened to "Expert-or-bust" levels in future releases.

## First-Run Demo

The `make demo` command provides a quick validation of expert-level performance:

```bash
make demo
```

**What the demo runs**:
- 2 definition queries (OSPF, TCP) with citation validation
- 2 concept cards (ARP, default route) with evidence checking
- 2 troubleshooting cases (OSPF neighbor down, interface issues) with step validation

**Output**: `DEMO: PASS` if all evaluations meet thresholds, `DEMO: FAIL` otherwise.

This ensures the system works for new users immediately and meets expert standards before any release.

## Run with Docker

### Quick Start with Docker

```bash
# Build and run with Docker Compose
make docker-run

# Or manually
docker build -t aev2:local .
docker compose up -d

# Check health
curl http://localhost:8001/healthz
```

### Docker Configuration

The Docker setup includes:
- **Base image**: `python:3.10-slim` for minimal size
- **Non-root user**: `aev2` user for security
- **Health checks**: Automatic health monitoring
- **Volume mounts**: Data directory mounted for persistence
- **Environment variables**: Configurable via docker-compose.yml

### Environment Variables

Key environment variables for Docker:
- `AE_BIND_PORT`: API port (default: 8001)
- `ENABLE_DENSE`: Enable dense embeddings (default: 0)
- `AE_INDEX_DIR`: Index directory path
- `AE_CACHE_ENABLED`: Enable TTL LRU cache (default: 0)
- `AE_CACHE_TTL_S`: Cache TTL in seconds (default: 300)
- `AE_CACHE_SIZE`: Maximum cache size (default: 1000)

## Performance

### HTTP Performance Testing

```bash
# Run performance test
make perf-http

# Or manually with custom parameters
python scripts/perf_http.py --base http://localhost:8001 --total 100 --concurrency 10 --json perf_http.json
```

### Performance Metrics

The performance harness measures:
- **Latency percentiles**: P50, P90, P95, P99
- **Throughput**: Requests per second
- **Success rate**: Percentage of successful requests
- **Error analysis**: Detailed error reporting

### Performance Tuning

**Environment Variables for Performance**:
- `AE_WORKERS`: Number of API workers (default: 1)
- `AE_CACHE_ENABLED`: Enable caching (default: 0)
- `AE_CACHE_TTL_S`: Cache TTL in seconds (default: 300)
- `AE_CACHE_SIZE`: Maximum cache size (default: 1000)

**Cache Configuration**:
```bash
# Enable cache with 60s TTL and 512 items
AE_CACHE_ENABLED=1 AE_CACHE_TTL_S=60 AE_CACHE_SIZE=512 python -m ae2.api.main
```

**Performance Reports**:
- `perf_http.json`: Detailed performance metrics
- `perf_metrics.prom`: Raw Prometheus metrics snapshot
- `perf_summary.json`: Combined performance and metrics summary
- CI artifacts: Performance reports uploaded to GitHub Actions
- Thresholds: P95 latency ≤ 250ms (configurable)

## Observability

### Structured Logging

AE v2 uses structured JSON logging for production observability:

```json
{
  "timestamp": 1640995200.123,
  "level": "INFO",
  "message": "Request completed",
  "req_id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "POST",
  "path": "/query",
  "status": 200,
  "lat_ms": 45.2,
  "intent": "DEFINE",
  "target": "2328",
  "cache_hit": false,
  "mode": "auto"
}
```

### Request Correlation

All requests are correlated using `X-Request-ID` headers:
- **Incoming**: Uses existing `X-Request-ID` header or generates new UUID
- **Outgoing**: Adds `X-Request-ID` to response headers
- **Logs**: All log entries include `req_id` field for correlation

### Metrics & Monitoring

**Prometheus Endpoint**: `/metrics`
- HTTP request latency histograms
- Router intent and target counters
- Query processing latency
- Cache hit/miss rates
- Concept compilation metrics
- Playbook execution metrics

**Health Checks**:
- `/healthz`: Lightweight health check (always OK if service running)
- `/readyz`: Readiness check (OK only if dependencies ready)

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AE_JSON_LOGS` | `1` | Enable structured JSON logging |
| `AE_LOG_SAMPLE` | `1.0` | Log sampling rate (0.0-1.0) |
| `AE_ENABLE_METRICS` | `1` | Enable Prometheus metrics |
| `AE_SERVICE_NAME` | `aev2` | Service name for metrics |
| `AE_CACHE_ENABLED` | `0` | Enable TTL LRU cache |
| `AE_CACHE_TTL_S` | `300` | Cache TTL in seconds |
| `AE_CACHE_SIZE` | `1000` | Maximum cache size |

## Development

### Continuous Integration

The project uses a **smoke-first CI strategy** to balance development velocity with quality:

#### CI Jobs

- **CI / test-api** (Required): Fast smoke tests (~30s) that gate all merges
  - Tests core API endpoints (`/healthz`, `/readyz`, `/query`, `/debug/index`)
  - Builds RFC index and uploads as artifact
  - Must pass for any merge to main

- **CI / ci-full** (Optional): Full test suite with comprehensive validation
- **CI / eval** (Optional): Evaluation suite with golden test cases
- **CI / perf** (Optional): Performance benchmarks and metrics

#### Running Full CI

**Option 1: Commit Flag**
```bash
git commit -m "feat: add new feature [full-ci]"
```

**Option 2: Manual Trigger**
1. Go to **Actions** → **CI** workflow
2. Click **Run workflow** button
3. Select branch and run

**Option 3: Scheduled**
- Full CI runs automatically at 8:15 AM UTC daily

#### Development Workflow

1. **Push to feature branch** → Smoke test runs automatically
2. **Open PR** → Only smoke test gates merge
3. **Merge when green** → Fast feedback loop
4. **Optional**: Add `[full-ci]` to commit for full validation

This approach ensures rapid iteration while maintaining quality through the reliable smoke test gate.

### Project Structure

```
ae2/
├── ae2/                    # Main package
│   ├── api/               # FastAPI application
│   ├── assembler/         # Response assembly
│   ├── contracts/         # Pydantic models
│   ├── retriever/         # Search and ranking
│   ├── router/            # Query routing
│   ├── rfc/              # RFC processing
│   ├── storage/          # Index management
│   └── testing/          # Test suites
├── data/                  # Data storage
│   ├── index/            # Search indexes
│   ├── rfc_index/        # RFC sections
│   ├── concepts/         # Concept cards
│   └── playbooks/        # Troubleshooting playbooks
├── scripts/              # Utility scripts
└── tests/                # Test files
```

### Code Quality

```bash
# Formatting
black ae2/
isort ae2/

# Linting
ruff check ae2/
mypy ae2/ --ignore-missing-imports

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

### Adding New Features

1. **Define contracts**: Add Pydantic models in `ae2/contracts/models.py`
2. **Implement logic**: Create modules in appropriate packages
3. **Add tests**: Write unit and integration tests
4. **Update API**: Add endpoints in `ae2/api/main.py`
5. **Document**: Update README and docstrings

## Performance

### Benchmarks

- **Query response time**: < 500ms average
- **Index building**: ~2 minutes for 1000 RFC sections
- **Memory usage**: ~2GB for full index
- **Storage**: ~500MB for complete RFC corpus

### Optimization

- **Embedding model**: Uses lightweight `all-MiniLM-L6-v2` (384d)
- **Hybrid ranking**: Combines dense embeddings with BM25 sparse retrieval
- **Caching**: Embeddings cached in memory for fast retrieval
- **Batch processing**: RFC sync processes documents in batches

## Scientific Rigor

### Data Integrity

- **Content-addressed storage**: All content has SHA256 hashes
- **Manifests**: Index metadata with integrity checks
- **Validation**: Pydantic models ensure type safety
- **Reproducibility**: Deterministic processing pipeline

### Testing Strategy

- **Unit tests**: Individual component validation
- **Integration tests**: End-to-end workflow testing
- **Golden tests**: Predefined test cases with expected outcomes
- **Performance tests**: Latency and throughput validation

### Monitoring

- **Health checks**: Component status monitoring
- **Debug endpoints**: Detailed system information
- **Logging**: Structured logging with correlation IDs
- **Metrics**: Processing time and confidence tracking

## Migration from v1

AE v2 is designed as a clean-slate implementation. Migration path:

1. **Parallel deployment**: Run v1 and v2 simultaneously
2. **Data export**: Export v1 RFC sections to v2 format
3. **Feature parity**: Implement core functionality in v2
4. **Validation**: Compare v1 vs v2 responses
5. **Cutover**: Switch to v2 when validation passes

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run the full test suite
5. Submit a pull request

### Development Guidelines

- Follow scientific rigor mandate
- Add comprehensive tests
- Update documentation
- Use type hints
- Follow PEP 8 style

## License

MIT License - see LICENSE file for details.

## Support

- **Issues**: GitHub Issues
- **Documentation**: This README and inline docstrings
- **API Docs**: Available at `/docs` when running in debug mode

## CI Artifacts

The following artifacts are generated by CI:

- **python-dist**: Built wheels and source distributions
- **sbom.json**: Software Bill of Materials (CycloneDX format)
- **pip_audit.json**: Security audit results from pip-audit

## Roadmap

### Phase 1 (Complete)
- [x] Core contracts and models
- [x] RFC intake pipeline
- [x] Hybrid ranker
- [x] Definition assembler
- [x] API with health checks
- [x] Golden test suite

### Phase 2 (In Progress)
- [ ] Concept cards implementation
- [ ] Evidence linking
- [ ] Lab integration
- [ ] Vendor command IR

### Phase 3 (Complete)
- [x] Troubleshooting playbooks
- [x] OSPF neighbor-down playbook
- [x] BGP neighbor-down playbook
- [x] Vendor command IR (IOS-XE, Junos)
- [x] Deterministic rule execution

### Phase 4 (Planned)
- [ ] Advanced routing
- [ ] Performance optimization
- [ ] Production deployment
