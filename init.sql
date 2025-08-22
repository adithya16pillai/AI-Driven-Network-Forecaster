-- Enable TimescaleDB extension if available (optional)
-- CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create network_metrics table
CREATE TABLE IF NOT EXISTS network_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    value DECIMAL(15,2) NOT NULL,
    unit VARCHAR(20),
    UNIQUE(timestamp, device_id, metric_name)
);

-- Create index for time-series queries
CREATE INDEX IF NOT EXISTS idx_network_metrics_time_device 
ON network_metrics (timestamp DESC, device_id);

-- Create predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    device_id VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    predicted_timestamp TIMESTAMPTZ NOT NULL,
    predicted_value DECIMAL(15,2) NOT NULL,
    confidence_interval_lower DECIMAL(15,2),
    confidence_interval_upper DECIMAL(15,2),
    model_version VARCHAR(50)
);
