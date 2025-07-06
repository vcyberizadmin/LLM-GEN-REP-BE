#!/usr/bin/env python3
"""
Automated backup script for LLM-GEN-REPORT Backend
Creates daily backups of uploaded files with retention management
"""

import os
import time
import tarfile
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Configuration from environment variables
UPLOAD_DIR = os.getenv('UPLOAD_DIR', '/app/data/uploads')
BACKUP_DIR = os.getenv('BACKUP_DIR', '/app/data/backups')
LOG_DIR = os.getenv('LOG_DIR', '/app/data/logs')
BACKUP_RETENTION_DAYS = int(os.getenv('BACKUP_RETENTION_DAYS', '14'))

# Set up logging
log_file = os.path.join(LOG_DIR, 'backup.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


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


def ensure_backup_dir():
    """Ensure backup directory exists"""
    backup_path = Path(BACKUP_DIR)
    backup_path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Backup directory: {BACKUP_DIR}")


def get_backup_filename() -> str:
    """Generate backup filename with timestamp"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"uploads_backup_{timestamp}.tar.gz"


def create_backup() -> Tuple[bool, str, int]:
    """Create compressed backup of upload directory"""
    if not os.path.exists(UPLOAD_DIR):
        logger.warning(f"Upload directory {UPLOAD_DIR} does not exist, skipping backup")
        return False, "", 0
    
    # Check if there are any files to backup
    upload_path = Path(UPLOAD_DIR)
    files_to_backup = list(upload_path.rglob('*'))
    file_count = sum(1 for f in files_to_backup if f.is_file())
    
    if file_count == 0:
        logger.info("No files found in upload directory, skipping backup")
        return False, "", 0
    
    backup_filename = get_backup_filename()
    backup_filepath = os.path.join(BACKUP_DIR, backup_filename)
    
    try:
        logger.info(f"Creating backup: {backup_filename}")
        logger.info(f"Backing up {file_count} files from {UPLOAD_DIR}")
        
        start_time = time.time()
        
        with tarfile.open(backup_filepath, 'w:gz') as tar:
            # Add the entire upload directory to the backup
            tar.add(UPLOAD_DIR, arcname='uploads')
        
        backup_time = time.time() - start_time
        backup_size = os.path.getsize(backup_filepath)
        
        logger.info(f"Backup created successfully in {backup_time:.2f} seconds")
        logger.info(f"Backup size: {format_size(backup_size)}")
        logger.info(f"Backup saved to: {backup_filepath}")
        
        return True, backup_filepath, backup_size
        
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        # Clean up partial backup file if it exists
        if os.path.exists(backup_filepath):
            try:
                os.remove(backup_filepath)
                logger.info("Cleaned up partial backup file")
            except Exception as cleanup_error:
                logger.warning(f"Could not clean up partial backup: {cleanup_error}")
        return False, "", 0


def cleanup_old_backups() -> Tuple[int, int]:
    """Remove old backup files beyond retention period"""
    cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)
    backups_removed = 0
    bytes_freed = 0
    
    try:
        backup_path = Path(BACKUP_DIR)
        if not backup_path.exists():
            logger.info("Backup directory does not exist")
            return 0, 0
        
        backup_files = []
        for file_path in backup_path.glob('uploads_backup_*.tar.gz'):
            if file_path.is_file():
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    backup_files.append((file_path, mtime))
                except Exception as e:
                    logger.warning(f"Error checking backup file {file_path}: {e}")
        
        old_backups = [f for f, mtime in backup_files if mtime < cutoff_date]
        
        if not old_backups:
            logger.info("No old backups found to clean up")
            return 0, 0
        
        logger.info(f"Found {len(old_backups)} old backups to remove")
        
        for backup_file in old_backups:
            try:
                file_size = backup_file.stat().st_size
                backup_file.unlink()
                backups_removed += 1
                bytes_freed += file_size
                logger.info(f"Removed old backup: {backup_file.name} ({format_size(file_size)})")
            except Exception as e:
                logger.error(f"Failed to remove backup {backup_file}: {e}")
    
    except Exception as e:
        logger.error(f"Error during backup cleanup: {e}")
    
    return backups_removed, bytes_freed


def verify_backup(backup_filepath: str) -> bool:
    """Verify backup file integrity"""
    try:
        logger.info(f"Verifying backup integrity: {backup_filepath}")
        with tarfile.open(backup_filepath, 'r:gz') as tar:
            # Try to list all files in the archive
            members = tar.getmembers()
            file_count = len([m for m in members if m.isfile()])
            logger.info(f"Backup verification successful: {file_count} files in archive")
            return True
    except Exception as e:
        logger.error(f"Backup verification failed: {e}")
        return False


def get_backup_stats():
    """Log current backup statistics"""
    try:
        backup_path = Path(BACKUP_DIR)
        if not backup_path.exists():
            logger.info("Backup directory does not exist")
            return
        
        backup_files = list(backup_path.glob('uploads_backup_*.tar.gz'))
        if not backup_files:
            logger.info("No backup files found")
            return
        
        total_size = sum(f.stat().st_size for f in backup_files)
        oldest_backup = min(backup_files, key=lambda f: f.stat().st_mtime)
        newest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
        
        oldest_date = datetime.fromtimestamp(oldest_backup.stat().st_mtime)
        newest_date = datetime.fromtimestamp(newest_backup.stat().st_mtime)
        
        logger.info(f"Backup stats: {len(backup_files)} backups, {format_size(total_size)} total")
        logger.info(f"Oldest backup: {oldest_date.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Newest backup: {newest_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.error(f"Error getting backup stats: {e}")


def main():
    """Main backup function"""
    logger.info("=" * 50)
    logger.info("Starting automated backup process")
    logger.info(f"Upload directory: {UPLOAD_DIR}")
    logger.info(f"Backup directory: {BACKUP_DIR}")
    logger.info(f"Backup retention: {BACKUP_RETENTION_DAYS} days")
    
    # Ensure backup directory exists
    ensure_backup_dir()
    
    # Log backup stats before operation
    logger.info("Backup stats before operation:")
    get_backup_stats()
    
    # Create new backup
    success, backup_path, backup_size = create_backup()
    
    # Verify backup if created successfully
    if success and backup_path:
        if verify_backup(backup_path):
            logger.info("✅ Backup created and verified successfully")
        else:
            logger.error("❌ Backup verification failed")
    
    # Clean up old backups
    if success:
        logger.info("Cleaning up old backups...")
        backups_removed, bytes_freed = cleanup_old_backups()
        logger.info(f"Old backups removed: {backups_removed}")
        logger.info(f"Space freed: {format_size(bytes_freed)}")
    
    # Log final backup stats
    logger.info("Backup stats after operation:")
    get_backup_stats()
    
    logger.info("Backup process finished")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()
