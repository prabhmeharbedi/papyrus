-- Initialize database schema for PDF Chat App
-- This file is run when the PostgreSQL container starts

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tables (these will be created by SQLAlchemy, but we can add indexes here)
-- The actual table creation is handled by the application's models.py

-- Add any additional database initialization here
-- For example, creating indexes for better performance:

-- Note: The actual table creation is handled by SQLAlchemy models
-- This file is for any additional database setup that needs to happen at startup