# Aetheriac Engine v2

A clean-slate implementation of the Aetheriac Engine with contract-first design, content-addressed storage, and modular architecture for network knowledge retrieval.

## Overview

AE v2 is a complete rewrite of the Aetheriac Engine with the following key improvements:

- **Contract-first design**: All data structures are defined as Pydantic models with validation
- **Content-addressed storage**: SHA256 hashes ensure data integrity and deduplication
- **Modular architecture**: Clear separation of concerns with independent packages
- **Scientific rigor**: Comprehensive testing, manifests, and traceable provenance
- **Performance**: Hybrid dense/sparse retrieval with sub-500ms response times

## Architecture

### Core Components

- **Contracts** (`ae2/contracts/`): Pydantic models defining all data structures
- **RFC Intake** (`ae2/rfc/`): Downloads and sectionizes RFC documents
- **Retriever** (`ae2/retriever/`): Hybrid dense/sparse search with BM25 + embeddings
- **Router** (`ae2/router/`): Query classification and routing
- **Assembler** (`ae2/assembler/`): Response construction from retrieved content
- **API** (`ae2/api/`): FastAPI application with health checks and debug endpoints
- **Storage** (`ae2/storage/`): Index management and content-addressed storage

### Data Flow

1. **RFC Sync**: Downloads RFC documents and sectionizes them into searchable chunks
2. **Index Building**: Creates hybrid indexes (dense embeddings + BM25 sparse)
3. **Query Processing**: 
   - Router classifies query intent
   - Retriever finds relevant sections
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
API_HOST=0.0.0.0
API_PORT=8000

# Feature flags
ENABLE_RFC=true
STRICT_DEFINITIONS=true
ENABLE_PLAYBOOKS=false

# Model settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
HYBRID_WEIGHT=0.7

# Data directories
DATA_DIR=data
INDEX_DIR=data/index
RFC_DIR=data/rfc_index
```

## Usage

### Starting the API

```bash
# Start the API server
python -m ae2.api.main

# Or use the CLI
ae2-api
```

The API will be available at `http://localhost:8000`

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