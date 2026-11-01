FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy dependency file AND source code (setuptools needs src/ to find packages)
COPY pyproject.toml .
COPY src/ src/

# Install Python dependencies + package
RUN pip install --no-cache-dir .

# Copy evaluation scripts (not needed for install, but needed at runtime)
COPY evaluation/ evaluation/

# Run as an unprivileged user
RUN useradd --create-home --uid 10001 app && mkdir -p /app/uploads && chown -R app /app
USER app

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]