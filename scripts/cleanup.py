#!/usr/bin/env python3
"""
Automated file cleanup script for LLM-GEN-REPORT Backend
Removes uploaded files older than specified retention period
"""

import os
import time
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Configuration from environment variables
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/app/data/uploads')
LOG_DIR = os.getenv('LOG_DIR', '/app/data/logs')
FILE_RETENTION_DAYS = int(os.getenv('FILE_RETENTION_DAYS', '7'))

# Set up logging
log_file = os.path.join(LOG_DIR, 'cleanup.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_dir_size(path: str) -> int:
    """Calculate total size of directory in bytes"""
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
    except Exception as e:
        logger.warning(f"Error calculating size for {path}: {e}")
    return total_size


def format_size(size_bytes: int) -> str:
    """Format bytes to human readable format"""
    if size_bytes == 0:
        return "0 B"
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_names[i]}"


def find_old_files() -> List[Tuple[str, datetime]]:
    """Find files older than retention period"""
    old_files = []
    cutoff_date = datetime.now() - timedelta(days=FILE_RETENTION_DAYS)
    
    try:
        upload_path = Path(UPLOAD_DIR)
        if not upload_path.exists():
            logger.info(f"Upload directory {UPLOAD_DIR} does not exist")
            return old_files
        
        for file_path in upload_path.rglob('*'):
            if file_path.is_file():
                try:
                    # Get file modification time
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        old_files.append((str(file_path), mtime))
                except Exception as e:
                    logger.warning(f"Error checking file {file_path}: {e}")
    
    except Exception as e:
        logger.error(f"Error scanning upload directory: {e}")
    
    return old_files


def cleanup_old_files() -> Tuple[int, int]:
    """Remove old files and return (files_removed, bytes_freed)"""
    old_files = find_old_files()
    files_removed = 0
    bytes_freed = 0
    
    if not old_files:
        logger.info("No old files found to clean up")
        return 0, 0
    
    logger.info(f"Found {len(old_files)} files older than {FILE_RETENTION_DAYS} days")
    
    for file_path, mtime in old_files:
        try:
            # Get file size before deletion
            file_size = os.path.getsize(file_path)
            
            # Remove the file
            os.remove(file_path)
            files_removed += 1
            bytes_freed += file_size
            
            logger.info(f"Removed: {file_path} ({format_size(file_size)}, modified: {mtime})")
            
        except Exception as e:
            logger.error(f"Failed to remove {file_path}: {e}")
    
    return files_removed, bytes_freed


def cleanup_empty_directories():
    """Remove empty directories in upload folder"""
    try:
        upload_path = Path(UPLOAD_DIR)
        if not upload_path.exists():
            return
        
        # Walk bottom-up to remove empty subdirectories first
        for dirpath, dirnames, filenames in os.walk(upload_path, topdown=False):
            if dirpath == str(upload_path):
                continue  # Don't remove the root upload directory
            
            try:
                if not os.listdir(dirpath):  # Directory is empty
                    os.rmdir(dirpath)
                    logger.info(f"Removed empty directory: {dirpath}")
            except Exception as e:
                logger.warning(f"Could not remove directory {dirpath}: {e}")
    
    except Exception as e:
        logger.error(f"Error cleaning empty directories: {e}")


def get_storage_stats():
    """Log current storage statistics"""
    try:
        if os.path.exists(UPLOAD_DIR):
            total_size = get_dir_size(UPLOAD_DIR)
            file_count = sum(1 for _ in Path(UPLOAD_DIR).rglob('*') if _.is_file())
            logger.info(f"Storage stats: {file_count} files, {format_size(total_size)} total")
        else:
            logger.info("Upload directory does not exist")
    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")


def main():
    """Main cleanup function"""
    logger.info("=" * 50)
    logger.info("Starting automated file cleanup")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Retention period: {FILE_RETENTION_DAYS} days")
    
    # Log storage stats before cleanup
    logger.info("Storage before cleanup:")
    get_storage_stats()
    
    # Perform cleanup
    start_time = time.time()
    files_removed, bytes_freed = cleanup_old_files()
    cleanup_empty_directories()
    cleanup_time = time.time() - start_time
    
    # Log results
    logger.info(f"Cleanup completed in {cleanup_time:.2f} seconds")
    logger.info(f"Files removed: {files_removed}")
    logger.info(f"Space freed: {format_size(bytes_freed)}")
    
    # Log storage stats after cleanup
    logger.info("Storage after cleanup:")
    get_storage_stats()
    
    logger.info("Cleanup process finished")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
