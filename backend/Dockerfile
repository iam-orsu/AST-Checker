FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 20.x for JavaScript AST analysis via acorn
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install acorn in the app directory so require() works from Node subprocess
WORKDIR /app
RUN npm init -y && npm install acorn

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build tree-sitter C++ grammar
RUN python -c "\
import tree_sitter_cpp as tscpp; \
import tree_sitter as ts; \
CPP_LANGUAGE = ts.Language(tscpp.language()); \
print('tree-sitter-cpp grammar loaded successfully')"

# Copy application code
COPY . .

# Create data directory for SQLite
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
