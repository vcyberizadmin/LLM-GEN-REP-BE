# Railway Deployment Guide

This guide covers deploying the LLM-GEN-REPORT Backend to Railway with Docker, persistent volumes, and automated file management.

## 🚀 Features

- **Dockerized Application**: Production-ready container with multi-stage build
- **25MB File Upload Limit**: Optimized for reasonable file sizes with configurable limits
- **Persistent Storage**: Mounted volumes for file uploads and backups
- **Automated Cleanup**: Daily cleanup of files older than 7 days
- **Automated Backups**: Daily compressed backups with 14-day retention
- **Admin Endpoints**: Manual triggers for cleanup and backup processes
- **Storage Monitoring**: Real-time storage statistics and monitoring

## 📁 Project Structure

```
├── Dockerfile                     # Production container configuration
├── docker-compose.yml            # Local development setup
├── railway.json                  # Railway deployment configuration
├── .dockerignore                 # Docker build context optimization
├── .env.example                  # Environment variables template
├── scripts/
│   ├── init.sh                   # Container initialization script
│   ├── cleanup.py                # Automated file cleanup
│   ├── backup.py                 # Automated backup system
│   └── crontab                   # Cron schedule for automation
└── backend/
    └── main.py                   # Updated with admin endpoints
```

## 🛠️ Setup Instructions

### 1. Prerequisites

- Railway account
- GitHub repository connected to Railway
- Anthropic API key

### 2. Environment Variables

Set these in Railway's environment variables:

```bash
# Required
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional (defaults provided)
UPLOAD_DIR=/app/data/uploads
BACKUP_DIR=/app/data/backups
LOG_DIR=/app/data/logs
MAX_FILE_SIZE_MB=25
FILE_RETENTION_DAYS=7
BACKUP_RETENTION_DAYS=14
ENVIRONMENT=production
PORT=8000
```

### 3. Railway Volume Configuration

Create a volume in Railway:
- **Volume Name**: `app-data`
- **Mount Path**: `/app/data`
- **Size**: 50-100GB (depending on usage)

### 4. Deploy to Railway

1. Connect your GitHub repository to Railway
2. Railway will automatically detect the `railway.json` configuration
3. Set environment variables in Railway dashboard
4. Deploy the application

## 🐳 Docker Configuration

### Multi-Stage Build

The Dockerfile uses a multi-stage build for optimized production images:
- **Builder stage**: Installs dependencies and creates virtual environment
- **Production stage**: Lightweight runtime with security best practices

### Security Features

- Non-root user (`appuser`)
- Minimal base image (Python 3.11-slim)
- Health checks
- Proper file permissions

## 📊 File Management

### Upload Configuration

- **Max file size**: 25MB (configurable via `MAX_FILE_SIZE_MB`)
- **Supported formats**: CSV, Excel (xlsx, xls, xlsm, xlsb), ODF (ods, odt)
- **Storage location**: `/app/data/uploads`

### Automatic Cleanup

- **Schedule**: Daily at 2:00 AM UTC
- **Retention**: 7 days (configurable via `FILE_RETENTION_DAYS`)
- **Process**: Removes files older than retention period
- **Logging**: Detailed logs in `/app/data/logs/cleanup.log`

### Automatic Backup

- **Schedule**: Daily at 3:00 AM UTC
- **Format**: Compressed tar.gz archives
- **Retention**: 14 days (configurable via `BACKUP_RETENTION_DAYS`)
- **Storage**: `/app/data/backups`
- **Verification**: Automatic integrity checks
- **Logging**: Detailed logs in `/app/data/logs/backup.log`

## 🔧 Admin Endpoints

### Manual Cleanup
```bash
POST /admin/cleanup
```
Manually trigger file cleanup process.

### Manual Backup
```bash
POST /admin/backup
```
Manually trigger backup creation.

### Storage Statistics
```bash
GET /admin/storage-stats
```
Get current storage usage and configuration.

**Example Response:**
```json
{
  "upload_directory": {
    "path": "/app/data/uploads",
    "size": "45.67 MB",
    "size_bytes": 47892234,
    "file_count": 23
  },
  "backup_directory": {
    "path": "/app/data/backups",
    "size": "12.34 MB",
    "size_bytes": 12943872,
    "backup_count": 5
  },
  "total_storage": {
    "size": "58.01 MB",
    "size_bytes": 60836106
  },
  "configuration": {
    "max_file_size_mb": 25,
    "file_retention_days": 7,
    "backup_retention_days": 14
  }
}
```

## 🏃 Local Development

### Using Docker Compose

```bash
# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Start the application
docker-compose up --build

# Application will be available at http://localhost:8000
```

### Development Features

- Volume mounts for live code reloading
- Local data persistence in `./data` directory
- Development environment configuration

## 📋 Monitoring and Logs

### Application Logs

- **App logs**: `/app/data/logs/app.log`
- **Cleanup logs**: `/app/data/logs/cleanup.log`
- **Backup logs**: `/app/data/logs/backup.log`

### Health Checks

- **Endpoint**: `GET /health`
- **Docker health check**: Built-in container health monitoring
- **Interval**: Every 30 seconds

### Storage Monitoring

Monitor storage usage via:
- Admin storage stats endpoint
- Container logs
- Railway metrics dashboard

## 🚨 Troubleshooting

### Common Issues

1. **Large file uploads failing**
   - Check `MAX_FILE_SIZE_MB` environment variable
   - Verify Railway request timeout settings

2. **Storage full**
   - Check storage stats via `/admin/storage-stats`
   - Manually trigger cleanup via `/admin/cleanup`
   - Consider increasing retention periods

3. **Backup failures**
   - Check backup logs in `/app/data/logs/backup.log`
   - Verify volume permissions
   - Check available disk space

### Log Analysis

```bash
# View cleanup logs
curl https://your-app.railway.app/admin/storage-stats

# Trigger manual cleanup
curl -X POST https://your-app.railway.app/admin/cleanup

# Trigger manual backup
curl -X POST https://your-app.railway.app/admin/backup
```

## 📈 Scaling Considerations

### Resource Requirements

- **Memory**: 1-2GB (sufficient for 25MB files)
- **CPU**: 1 core minimum
- **Storage**: 50-100GB persistent volume
- **Network**: Standard bandwidth

### Performance Optimization

- Files are processed in memory (efficient for 25MB limit)
- Automated cleanup prevents storage buildup
- Compressed backups minimize storage usage
- Health checks ensure application reliability

## 🔐 Security

### Container Security

- Non-root user execution
- Minimal attack surface
- Regular security updates via base image

### Data Security

- Files stored in persistent volumes
- Automatic cleanup of old files
- Backup verification and integrity checks

### Access Control

- Admin endpoints for management
- Environment-based configuration
- Secure API key handling

## 📚 Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

## 🎯 Next Steps

1. Deploy to Railway following this guide
2. Set up monitoring and alerting
3. Configure custom domain (optional)
4. Set up CI/CD pipeline for automated deployments
5. Configure backup retention policies based on requirements

---

**Note**: This deployment configuration is optimized for production use with Railway's infrastructure. Adjust resource allocations and retention policies based on your specific usage patterns and requirements.
