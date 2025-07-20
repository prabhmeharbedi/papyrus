#!/bin/bash

# Production startup script for PDF Chat App

set -e

echo "Starting PDF Chat App..."

# Check if running in Docker (no venv needed)
if [ ! -f /.dockerenv ]; then
    # Activate virtual environment if not in Docker
    if [ -d "venv" ]; then
        echo "Activating virtual environment..."
        source venv/bin/activate
    fi
fi

# Wait for database to be ready (if DATABASE_URL is set)
if [ ! -z "$DATABASE_URL" ]; then
    echo "Waiting for database..."
    # Extract database connection details from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
    
    # Use default values if extraction fails
    DB_HOST=${DB_HOST:-localhost}
    DB_PORT=${DB_PORT:-5432}
    DB_USER=${DB_USER:-pdf_chat_user}
    
    # Wait for database with timeout
    timeout=30
    while ! pg_isready -h $DB_HOST -p $DB_PORT -U $DB_USER 2>/dev/null; do
        echo "Database not ready, waiting..."
        sleep 2
        timeout=$((timeout-2))
        if [ $timeout -le 0 ]; then
            echo "Database connection timeout"
            break
        fi
    done
    echo "Database is ready!"
fi

# Create database tables if they don't exist
if [ -f "create_tables.py" ]; then
    echo "Setting up database..."
    python create_tables.py
fi

# Start the application
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Starting in production mode with Gunicorn..."
    echo "API will be available at: http://0.0.0.0:8000"
    echo "Health check available at: http://0.0.0.0:8000/health"
    echo ""
    exec gunicorn main:app \
        --bind 0.0.0.0:8000 \
        --workers ${MAX_WORKERS:-4} \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout ${REQUEST_TIMEOUT:-300} \
        --keep-alive 2 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level ${LOG_LEVEL:-info}
else
    echo "Starting in development mode with Uvicorn..."
    echo "API will be available at: http://localhost:8000"
    echo "API docs will be available at: http://localhost:8000/docs"
    echo "Health check available at: http://localhost:8000/health"
    echo ""
    exec uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level ${LOG_LEVEL:-info}
fi