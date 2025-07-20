# PDF Chat App Deployment Guide

This guide covers deploying the PDF Chat App in various environments.

## Quick Start with Docker Compose

### Prerequisites
- Docker and Docker Compose installed
- RAGFlow instance running (can be local or remote)

### Steps

1. **Clone and prepare environment**:
   ```bash
   git clone <repository-url>
   cd pdf-chat-app
   cp backend/.env.example .env
   ```

2. **Configure environment variables**:
   Edit `.env` file with your settings:
   ```bash
   RAGFLOW_API_URL=http://your-ragflow-instance:9380
   RAGFLOW_API_KEY=your_api_key
   SECRET_KEY=your_secure_secret_key
   ```

3. **Start the application**:
   ```bash
   docker-compose up -d
   ```

4. **Access the application**:
   - Frontend: http://localhost:8000
   - API: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Production Deployment

### Environment Configuration

Create a production environment file:
```bash
cp backend/.env.production .env
```

Update the following critical settings:
- `SECRET_KEY`: Use a strong, unique secret key
- `DEBUG=False`: Disable debug mode
- `ALLOWED_ORIGINS`: Set to your domain(s)
- `DATABASE_URL`: Production database connection
- `RAGFLOW_API_URL`: Production RAGFlow instance
- `LOG_LEVEL=INFO`: Appropriate logging level

### Docker Production Deployment

1. **Build production image**:
   ```bash
   docker build -t pdf-chat-app:latest .
   ```

2. **Run with production settings**:
   ```bash
   docker run -d \
     --name pdf-chat-app \
     -p 8000:8000 \
     --env-file .env \
     -v pdf_chat_uploads:/app/uploads \
     -v pdf_chat_logs:/app/logs \
     pdf-chat-app:latest
   ```

### Kubernetes Deployment

Example Kubernetes manifests:

**Deployment:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pdf-chat-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: pdf-chat-app
  template:
    metadata:
      labels:
        app: pdf-chat-app
    spec:
      containers:
      - name: pdf-chat-app
        image: pdf-chat-app:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        envFrom:
        - secretRef:
            name: pdf-chat-secrets
        livenessProbe:
          httpGet:
            path: /live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
```

**Service:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: pdf-chat-service
spec:
  selector:
    app: pdf-chat-app
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## Health Checks and Monitoring

### Health Check Endpoints

- `/health` - Basic health check
- `/health/detailed` - Detailed health with dependency status
- `/ready` - Kubernetes readiness probe
- `/live` - Kubernetes liveness probe
- `/metrics` - Application metrics (if enabled)

### Monitoring Setup

1. **Enable metrics**:
   ```bash
   ENABLE_METRICS=True
   ```

2. **Log aggregation**:
   Configure log file location:
   ```bash
   LOG_FILE=logs/app.log
   LOG_LEVEL=INFO
   ```

3. **Health check monitoring**:
   Set up monitoring to check `/health/detailed` endpoint regularly.

## Database Setup

### PostgreSQL

1. **Create database and user**:
   ```sql
   CREATE DATABASE pdf_chat_db;
   CREATE USER pdf_chat_user WITH PASSWORD 'secure_password';
   GRANT ALL PRIVILEGES ON DATABASE pdf_chat_db TO pdf_chat_user;
   ```

2. **Connection string**:
   ```bash
   DATABASE_URL=postgresql://pdf_chat_user:secure_password@localhost:5432/pdf_chat_db
   ```

### Database Migrations

The application automatically creates tables on startup. For production, consider:
- Running migrations separately
- Using database migration tools
- Backing up before updates

## Security Considerations

### Production Security Checklist

- [ ] Use strong `SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure proper `ALLOWED_ORIGINS`
- [ ] Use HTTPS in production
- [ ] Secure database connections
- [ ] Limit file upload sizes
- [ ] Regular security updates
- [ ] Monitor logs for suspicious activity

### File Upload Security

- Maximum file size: Configurable via `MAX_FILE_SIZE`
- Allowed file types: PDF only
- File storage: Isolated upload directory
- Cleanup: Configurable via `ENABLE_FILE_CLEANUP`

## Performance Tuning

### Application Settings

```bash
# Worker processes
MAX_WORKERS=8

# Request timeout
REQUEST_TIMEOUT=300

# File size limits
MAX_FILE_SIZE=52428800  # 50MB
```

### Database Optimization

- Connection pooling (handled by SQLAlchemy)
- Regular VACUUM and ANALYZE
- Appropriate indexes on frequently queried columns

### Caching

Redis is used for:
- Session storage
- Caching frequently accessed data
- Background task queues

## Troubleshooting

### Common Issues

1. **Database connection failed**:
   - Check `DATABASE_URL` format
   - Verify database server is running
   - Check network connectivity

2. **RAGFlow connection failed**:
   - Verify `RAGFLOW_API_URL` and `RAGFLOW_API_KEY`
   - Check RAGFlow service status
   - Review network connectivity

3. **File upload issues**:
   - Check disk space in upload directory
   - Verify file permissions
   - Review `MAX_FILE_SIZE` setting

4. **High memory usage**:
   - Reduce `MAX_WORKERS`
   - Monitor document processing
   - Check for memory leaks in logs

### Log Analysis

Logs are structured with timestamps and levels:
```
2024-01-01 12:00:00 - main - INFO - Application started
2024-01-01 12:00:01 - main - ERROR - Database connection failed
```

Key log patterns to monitor:
- Database connection errors
- RAGFlow API failures
- File processing errors
- High response times

## Backup and Recovery

### Database Backup

```bash
# Create backup
pg_dump -h localhost -U pdf_chat_user pdf_chat_db > backup.sql

# Restore backup
psql -h localhost -U pdf_chat_user pdf_chat_db < backup.sql
```

### File Backup

```bash
# Backup uploads directory
tar -czf uploads_backup.tar.gz uploads/

# Restore uploads
tar -xzf uploads_backup.tar.gz
```

## Scaling

### Horizontal Scaling

- Multiple application instances behind load balancer
- Shared database and Redis instances
- Shared file storage (NFS, S3, etc.)

### Vertical Scaling

- Increase `MAX_WORKERS`
- Allocate more memory and CPU
- Optimize database resources

## Support

For issues and questions:
1. Check application logs
2. Review health check endpoints
3. Verify configuration settings
4. Check dependency service status