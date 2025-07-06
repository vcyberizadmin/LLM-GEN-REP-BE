# Multi-stage build for production
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/
COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir -r /tmp/backend-requirements.txt

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    cron \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create app user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Create application directories
WORKDIR /app
RUN mkdir -p /app/data/uploads /app/data/backups /app/data/logs /app/data/temp && \
    chown -R appuser:appuser /app

# Copy application code
COPY . /app/
RUN chown -R appuser:appuser /app

# Make scripts executable
RUN chmod +x /app/scripts/*.sh /app/scripts/*.py

# Set up cron for cleanup
COPY scripts/crontab /etc/cron.d/app-cleanup
RUN chmod 0644 /etc/cron.d/app-cleanup && \
    crontab -u appuser /etc/cron.d/app-cleanup

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Initialize and start application
CMD ["/app/scripts/init.sh"]
