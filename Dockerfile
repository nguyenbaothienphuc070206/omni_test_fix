# Builder Stage
FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential gcc python3-dev
RUN pip install --no-cache-dir cython numpy setuptools wheel
COPY . .
RUN python setup.py build_ext --inplace

# Runtime Stage
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app /app

# Explicitly install dependencies without the [standard] bloat to control versions
RUN pip install --no-cache-dir \
    fastapi==0.115.0 \
    uvicorn==0.30.6 \
    uvloop==0.20.0 \
    httptools==0.6.1 \
    websockets==13.1 \
    httpx \
    redis \
    asyncpg \
    sqlalchemy \
    pydantic \
    cython \
    numpy \
    python-multipart \
    prometheus-client

EXPOSE 8000

# Run with uvloop, disable websockets to avoid dependency conflicts
CMD ["uvicorn", "aegis_app:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--ws", "none"]
