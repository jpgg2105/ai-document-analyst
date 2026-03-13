FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency file first for layer caching
COPY pyproject.toml .

# Install Python dependencies
RUN pip install --no-cache-dir . 

# Copy application code
COPY src/ src/
COPY evaluation/ evaluation/

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
