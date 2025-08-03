FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r aev2 && useradd -r -g aev2 aev2

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Copy application code
COPY ae2/ ./ae2/

# Create data directory
RUN mkdir -p /app/data/index && chown -R aev2:aev2 /app

# Switch to non-root user
USER aev2

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/healthz || exit 1

# Copy serving script
COPY scripts/serve.sh /app/scripts/serve.sh

# Default command
CMD ["/app/scripts/serve.sh"]
