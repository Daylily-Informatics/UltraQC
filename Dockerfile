# ==============================================
# UltraQC - Modern MultiQC Data Aggregation
# Dockerfile for production deployment
# ==============================================

# Stage 1: Build frontend assets
FROM node:18-alpine AS frontend
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Python application
FROM python:3.11-slim

LABEL maintainer="Daylily Informatics <info@daylily.info>" \
    description="UltraQC - Modern MultiQC Data Aggregation Platform powered by FastAPI" \
    version="1.0.0"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ULTRAQC_PRODUCTION=1 \
    ULTRAQC_SECRET="SuperSecretValueYouShouldReallyChange" \
    ULTRAQC_HOST="0.0.0.0" \
    ULTRAQC_PORT="8000" \
    DB_HOST="127.0.0.1" \
    DB_PORT="5432" \
    DB_NAME="ultraqc" \
    DB_USER="ultraqc" \
    DB_PASS="ultraqcpswd"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application code
COPY . /app

# Copy compiled frontend assets from build stage
COPY --from=frontend /app/ultraqc/static/ /app/ultraqc/static/

# Install Python dependencies
RUN pip install --no-cache-dir /app[prod]

# Copy and set up start script
COPY ./start.sh /start.sh
RUN chmod +x /start.sh

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "ultraqc.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]