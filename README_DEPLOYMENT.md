# PDF Chat App - Deployment Features

This document describes the deployment and performance optimization features implemented in the PDF Chat App.

## 🚀 Quick Start

### Using Docker Compose (Recommended)

1. **Setup environment**:
   ```bash
   cp backend/.env.example .env
   # Edit .env with your RAGFlow settings
   ```

2. **Start all services**:
   ```bash
   docker compose up -d
   ```

3. **Access the application**:
   - Application: http://localhost:8000
   - Health Check: http://localhost:8000/health
   - API Docs: http://localhost:8000/docs

## 📊 Health Monitoring

### Health Check Endpoints

| Endpoint | Purpose | Use Case |
|----------|---------|----------|
| `/health` | Basic health status | Load balancer health checks |
| `/health/detailed` | Comprehensive health with dependencies | Monitoring dashboards |
| `/live` | Liveness probe | Kubernetes liveness probe |
| `/ready` | Readiness probe | Kubernetes readiness probe |
| `/metrics` | Application metrics | Performance monitoring |

### Example Health Check Response

```json
{
  "status": "healthy",
  "service": "pdf-chat-api",
  "timestamp": 1642781234.567,
  "environment": "production",
  "checks": {
    "database": {"status": "healthy", "message": "Connected"},
    "redis": {"status": "healthy", "message": "Connected"},
    "ragflow": {"status": "healthy", "message": "Connected"},
    "filesystem": {"status": "healthy", "message": "Read/write OK"}
  }
}
```

## 🔧 Configuration

### Environment Variables

#### Core Settings
- `RAGFLOW_API_URL` - RAGFlow instance URL
- `RAGFLOW_API_KEY` - RAGFlow API key
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret key

#### Security Settings
- `DEBUG` - Enable/disable debug mode (False for production)
- `ALLOWED_ORIGINS` - Comma-separated list of allowed origins
- `MAX_FILE_SIZE` - Maximum upload file size in bytes

#### Performance Settings
- `MAX_WORKERS` - Number of worker processes
- `REQUEST_TIMEOUT` - Request timeout in seconds
- `LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)

#### Feature Flags
- `ENABLE_METRICS` - Enable metrics endpoint
- `ENABLE_FILE_CLEANUP` - Enable automatic file cleanup
- `ENVIRONMENT` - Environment name (development, production)

## 🐳 Docker Configuration

### Multi-stage Build
The Dockerfile uses multi-stage builds for optimization:
1. **Frontend Builder**: Builds React application
2. **Backend Base**: Sets up Python environment and copies built frontend

### Security Features
- Non-root user execution
- Minimal base image (Python slim)
- Health checks built-in
- Proper file permissions

### Docker Compose Services
- **postgres**: PostgreSQL database with health checks
- **redis**: Redis cache with persistence
- **app**: Main application with dependency health checks

## 📝 Logging

### Structured Logging
- Timestamp, logger name, level, and message
- Configurable log levels
- File rotation (10MB max, 5 backups)
- Console and file output

### Log Configuration
```python
# Environment variables
LOG_LEVEL=INFO
LOG_FILE=logs/app.log

# Programmatic setup
from logging_config import setup_logging
setup_logging("INFO", "logs/app.log")
```

## 🛡️ Error Handling

### Custom Error Classes
- `APIError` - Base API error
- `DocumentProcessingError` - Document processing failures
- `RAGFlowError` - RAGFlow communication errors
- `DatabaseError` - Database operation errors

### Error Response Format
```json
{
  "status": "error",
  "message": "Human-readable error message",
  "error_code": "ERROR_TYPE",
  "details": {} // Optional additional details
}
```

## 🚀 Production Deployment

### Using Gunicorn (Production)
```bash
ENVIRONMENT=production ./start.sh
```

Features:
- Multiple worker processes
- Request timeout handling
- Graceful shutdowns
- Access and error logging
- Process recycling

### Kubernetes Deployment
The application includes:
- Liveness probes (`/live`)
- Readiness probes (`/ready`)
- Resource limits and requests
- Health check configurations

### Performance Optimizations
- Connection pooling (SQLAlchemy)
- Redis caching
- File upload validation
- Request timeout handling
- Worker process management

## 📈 Monitoring

### Metrics Available
When `ENABLE_METRICS=True`:
- Document counts by status
- Conversation and message counts
- File system usage
- Processing statistics

### Health Check Monitoring
Set up monitoring to regularly check:
- `/health/detailed` for comprehensive status
- Response time monitoring
- Error rate tracking
- Resource usage monitoring

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check `DATABASE_URL` format
   - Verify database server is running
   - Check network connectivity

2. **RAGFlow Connection Failed**
   - Verify `RAGFLOW_API_URL` and `RAGFLOW_API_KEY`
   - Check RAGFlow service status
   - Review network connectivity

3. **Redis Connection Failed**
   - Check `REDIS_URL` format
   - Verify Redis server is running
   - Application will work without Redis (degraded mode)

### Log Analysis
Monitor logs for:
- Database connection errors
- RAGFlow API failures
- File processing errors
- High response times
- Memory usage patterns

## 🔄 Updates and Maintenance

### Rolling Updates
1. Build new image
2. Update deployment
3. Health checks ensure smooth transition
4. Rollback capability via image tags

### Database Migrations
- Automatic table creation on startup
- Manual migration support
- Backup recommendations

### File Cleanup
When `ENABLE_FILE_CLEANUP=True`:
- Automatic cleanup of orphaned files
- Configurable retention policies
- Safe deletion with database consistency

## 📚 Additional Resources

- [Full Deployment Guide](DEPLOYMENT.md)
- [Docker Compose Configuration](docker-compose.yml)
- [Environment Examples](backend/.env.example)
- [Health Check Tests](backend/test_health_endpoints.py)

## 🆘 Support

For deployment issues:
1. Check health endpoints for service status
2. Review application logs
3. Verify environment configuration
4. Test individual service connections