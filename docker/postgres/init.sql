-- Clickstream Analytics Database Initialization
-- This script runs on first startup of PostgreSQL

-- Create database for Airflow
CREATE DATABASE airflow;

-- Create clickstream database (default from POSTGRES_DB)
-- Tables will be created in clickstream database

\c clickstream;

-- Clickstream events table
CREATE TABLE IF NOT EXISTS clicks (
    click_id          BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    session_id        VARCHAR(100) NOT NULL,
    page_url          TEXT NOT NULL,
    event_type        VARCHAR(50),
    event_timestamp   TIMESTAMP NOT NULL,
    user_agent        TEXT,
    ip_address        INET,
    referrer_url      TEXT,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for CDC and querying
CREATE INDEX IF NOT EXISTS idx_clicks_updated_at ON clicks(updated_at);
CREATE INDEX IF NOT EXISTS idx_clicks_event_timestamp ON clicks(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_clicks_user_id ON clicks(user_id);
CREATE INDEX IF NOT EXISTS idx_clicks_session_id ON clicks(session_id);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    session_id        VARCHAR(100) PRIMARY KEY,
    user_id           BIGINT NOT NULL,
    started_at        TIMESTAMP NOT NULL,
    ended_at          TIMESTAMP,
    duration_seconds  INT,
    page_views_count  INT DEFAULT 0,
    bounce            BOOLEAN DEFAULT false,
    traffic_source    VARCHAR(50),
    device_type       VARCHAR(50),
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for sessions
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started_at ON sessions(started_at);

-- Enable logical replication for CDC
ALTER SYSTEM SET wal_level = 'logical';
ALTER SYSTEM SET max_replication_slots = 10;
ALTER SYSTEM SET max_wal_senders = 10;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE clickstream TO admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;
