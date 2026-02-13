# Yahoo Services Dockerfile
# Multi-stage build for production

# Build stage
FROM python:3.13-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Runtime stage
FROM python:3.13-slim

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy application code
COPY . .

# Make sure scripts are executable
RUN chmod +x entrypoint.sh

# Add user's local bin to PATH
ENV PATH=/root/.local/bin:$PATH

# Create logs directory
RUN mkdir -p logs

# Expose ports (dev: 8085, prod: 8185, stage: 8285)
EXPOSE 8085 8185 8285

# Set default environment
ENV ENVIRONMENT=production

# Use entrypoint script
ENTRYPOINT ["./entrypoint.sh"]
