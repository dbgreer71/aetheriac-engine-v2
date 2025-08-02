# Aetheriac Engine v2

![CI](https://github.com/dbgreer71/aetheriac-engine-v2/actions/workflows/ci.yml/badge.svg)

A clean-slate implementation of the Aetheriac Engine with contract-first design, content-addressed storage, and modular architecture for network knowledge retrieval.

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

### Prerequisites

- Python 3.9+
- 4GB+ RAM (for embedding models)
- 2GB+ disk space

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd ae2

# Install dependencies
pip install -e ".[dev]"

# Set up environment
cp .env.example .env
# Edit .env with your configuration
```

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

### Starting the API

```bash
# Start the API server
python -m ae2.api.main

# Or with custom configuration
AE_INDEX_DIR="$(pwd)/data/index" AE_BIND_PORT=8001 ENABLE_DENSE=0 \
python -m ae2.api.main
```

The API will be available at `http://localhost:8000` (or configured port)

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

## Development

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

### Phase 3 (Planned)
- [ ] Troubleshooting playbooks
- [ ] Advanced routing
- [ ] Performance optimization
- [ ] Production deployment
