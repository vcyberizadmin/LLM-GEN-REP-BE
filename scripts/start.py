#!/usr/bin/env python3
"""
Simple Python startup script for Railway deployment
Falls back to basic uvicorn startup if shell script fails
"""

import os
import subprocess
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting LLM-GEN-REPORT Backend (Python startup)")
    
    # Set up environment variables with defaults
    upload_dir = os.getenv('UPLOAD_DIR', '/app/data/uploads')
    backup_dir = os.getenv('BACKUP_DIR', '/app/data/backups')
    log_dir = os.getenv('LOG_DIR', '/app/data/logs')
    port = os.getenv('PORT', '8000')
    
    # Create required directories
    try:
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(backup_dir, exist_ok=True)
        os.makedirs(log_dir, exist_ok=True)
        os.makedirs('/app/data/temp', exist_ok=True)
        logger.info(f"✅ Created directories: {upload_dir}, {backup_dir}, {log_dir}")
    except Exception as e:
        logger.warning(f"Directory creation failed: {e}")
    
    # Set working directory
    os.chdir('/app')
    
    logger.info(f"📁 Upload directory: {upload_dir}")
    logger.info(f"📦 Backup directory: {backup_dir}")
    logger.info(f"📋 Log directory: {log_dir}")
    logger.info(f"🌟 Starting FastAPI server on port {port}")
    
    # Start the FastAPI application
    try:
        subprocess.run([
            'uvicorn', 'backend.main:app',
            '--host', '0.0.0.0',
            '--port', port,
            '--log-level', 'info'
        ], check=True)
    except Exception as e:
        logger.error(f"Failed to start uvicorn: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
