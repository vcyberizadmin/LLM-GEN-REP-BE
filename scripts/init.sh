#!/bin/bash

# Container initialization script for Railway deployment
set -e

echo "🚀 Starting LLM-GEN-REPORT Backend..."

# Create required directories if they don't exist
mkdir -p /app/data/uploads /app/data/backups /app/data/logs /app/data/temp

# Set up log files
touch /app/data/logs/app.log
touch /app/data/logs/cleanup.log
touch /app/data/logs/backup.log

# Set up environment variables with defaults
export UPLOAD_DIR=${UPLOAD_DIR:-/app/data/uploads}
export BACKUP_DIR=${BACKUP_DIR:-/app/data/backups}
export LOG_DIR=${LOG_DIR:-/app/data/logs}
export MAX_FILE_SIZE_MB=${MAX_FILE_SIZE_MB:-25}
export FILE_RETENTION_DAYS=${FILE_RETENTION_DAYS:-7}
export BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-14}
export PORT=${PORT:-8000}

echo "📁 Upload directory: $UPLOAD_DIR"
echo "📦 Backup directory: $BACKUP_DIR"
echo "📋 Log directory: $LOG_DIR"
echo "📏 Max file size: ${MAX_FILE_SIZE_MB}MB"
echo "🗓️ File retention: ${FILE_RETENTION_DAYS} days"
echo "🗃️ Backup retention: ${BACKUP_RETENTION_DAYS} days"

# Start cron daemon for automated cleanup (if available)
if command -v cron >/dev/null 2>&1; then
    echo "⏰ Starting cron for automated cleanup..."
    cron || echo "Warning: Could not start cron daemon"
fi

# Run initial cleanup (non-blocking)
echo "🧹 Running initial cleanup..."
cd /app && python scripts/cleanup.py || echo "Warning: Initial cleanup failed, continuing anyway"

# Start the FastAPI application
echo "🌟 Starting FastAPI server on port $PORT..."
cd /app && uvicorn backend.main:app --host 0.0.0.0 --port $PORT --log-level info
