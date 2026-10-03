-- ============================================================
-- Weather AI Platform — Initial Database Schema
-- Run against PostgreSQL 15+
-- All timestamps stored in UTC.
-- ============================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Locations ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS locations (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(200) NOT NULL,
    city         VARCHAR(100),
    country      VARCHAR(100),
    latitude     DOUBLE PRECISION NOT NULL,
    longitude    DOUBLE PRECISION NOT NULL,
    elevation_m  DOUBLE PRECISION,
    timezone     VARCHAR(50)  DEFAULT 'UTC',
    is_active    BOOLEAN      DEFAULT TRUE,
    created_at   TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_locations_name      ON locations (name);
CREATE INDEX IF NOT EXISTS ix_locations_city      ON locations (city);
CREATE INDEX IF NOT EXISTS ix_locations_lat_lon   ON locations (latitude, longitude);

-- ── Historical weather observations ──────────────────────────
CREATE TABLE IF NOT EXISTS weather_observations (
    id                  SERIAL PRIMARY KEY,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    observed_at         TIMESTAMPTZ NOT NULL,
    source              VARCHAR(50)  DEFAULT 'station',
    temperature_c       DOUBLE PRECISION,
    feels_like_c        DOUBLE PRECISION,
    dew_point_c         DOUBLE PRECISION,
    humidity_pct        DOUBLE PRECISION,
    pressure_hpa        DOUBLE PRECISION,
    wind_speed_kmh      DOUBLE PRECISION,
    wind_direction_deg  DOUBLE PRECISION,
    wind_gust_kmh       DOUBLE PRECISION,
    precipitation_mm    DOUBLE PRECISION,
    precipitation_1h_mm DOUBLE PRECISION,
    solar_radiation_wm2 DOUBLE PRECISION,
    visibility_m        DOUBLE PRECISION,
    cloud_cover_pct     DOUBLE PRECISION,
    quality_flag        VARCHAR(10)  DEFAULT 'OK',
    created_at          TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_obs_location_time ON weather_observations (location_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_obs_observed_at   ON weather_observations (observed_at DESC);

-- ── Weather Union observations ────────────────────────────────
CREATE TABLE IF NOT EXISTS weather_union_observations (
    id                  SERIAL PRIMARY KEY,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    station_id          VARCHAR(100) NOT NULL,
    station_name        VARCHAR(200),
    observed_at         TIMESTAMPTZ NOT NULL,
    fetched_at          TIMESTAMPTZ  DEFAULT NOW(),
    temperature_c       DOUBLE PRECISION,
    humidity_pct        DOUBLE PRECISION,
    wind_speed_kmh      DOUBLE PRECISION,
    wind_direction_deg  DOUBLE PRECISION,
    precipitation_mm    DOUBLE PRECISION,
    pressure_hpa        DOUBLE PRECISION,
    station_latitude    DOUBLE PRECISION,
    station_longitude   DOUBLE PRECISION,
    is_valid            BOOLEAN      DEFAULT TRUE,
    raw_response        TEXT
);
CREATE INDEX IF NOT EXISTS ix_wu_station_time  ON weather_union_observations (station_id, observed_at DESC);
CREATE INDEX IF NOT EXISTS ix_wu_location_time ON weather_union_observations (location_id, observed_at DESC);

-- ── NWP forecast data ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS nwp_forecasts (
    id                  SERIAL PRIMARY KEY,
    location_id         INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    model_name          VARCHAR(20) NOT NULL,   -- GFS, ECMWF, JMA
    run_time            TIMESTAMPTZ NOT NULL,   -- model initialisation time
    valid_time          TIMESTAMPTZ NOT NULL,   -- forecast valid for this time
    horizon_hours       INTEGER NOT NULL,
    temperature_c       DOUBLE PRECISION,
    humidity_pct        DOUBLE PRECISION,
    wind_speed_kmh      DOUBLE PRECISION,
    wind_direction_deg  DOUBLE PRECISION,
    precipitation_mm    DOUBLE PRECISION,
    pressure_hpa        DOUBLE PRECISION,
    cloud_cover_pct     DOUBLE PRECISION,
    fetched_at          TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_nwp_loc_model_valid ON nwp_forecasts (location_id, model_name, valid_time DESC);
CREATE INDEX IF NOT EXISTS ix_nwp_valid_time       ON nwp_forecasts (valid_time DESC);

-- ── Forecast runs (metadata per generation cycle) ─────────────
CREATE TABLE IF NOT EXISTS forecast_runs (
    id                       SERIAL PRIMARY KEY,
    started_at               TIMESTAMPTZ  DEFAULT NOW(),
    completed_at             TIMESTAMPTZ,
    status                   VARCHAR(20)  DEFAULT 'running',
    gfs_available            BOOLEAN      DEFAULT FALSE,
    ecmwf_available          BOOLEAN      DEFAULT FALSE,
    jma_available            BOOLEAN      DEFAULT FALSE,
    weather_union_available  BOOLEAN      DEFAULT FALSE,
    error_message            TEXT,
    meta                     JSONB
);

-- ── ML model predictions ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS model_predictions (
    id                       SERIAL PRIMARY KEY,
    location_id              INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    forecast_run_id          INTEGER REFERENCES forecast_runs(id),
    predicted_at             TIMESTAMPTZ  DEFAULT NOW(),
    valid_time               TIMESTAMPTZ NOT NULL,
    horizon_hours            INTEGER NOT NULL,
    -- HEAD 1: Weather prediction
    temperature_c            DOUBLE PRECISION,
    humidity_pct             DOUBLE PRECISION,
    wind_speed_kmh           DOUBLE PRECISION,
    wind_direction_deg       DOUBLE PRECISION,
    precipitation_mm         DOUBLE PRECISION,
    pressure_hpa             DOUBLE PRECISION,
    -- HEAD 2: Uncertainty
    temperature_uncertainty  DOUBLE PRECISION,
    humidity_uncertainty     DOUBLE PRECISION,
    wind_speed_uncertainty   DOUBLE PRECISION,
    precipitation_uncertainty DOUBLE PRECISION,
    confidence_score         DOUBLE PRECISION,
    -- Dynamic weights used
    gfs_weight               DOUBLE PRECISION,
    ecmwf_weight             DOUBLE PRECISION,
    jma_weight               DOUBLE PRECISION,
    ml_weight                DOUBLE PRECISION
);
CREATE INDEX IF NOT EXISTS ix_pred_loc_valid ON model_predictions (location_id, valid_time DESC);

-- ── Model performance tracking ────────────────────────────────
CREATE TABLE IF NOT EXISTS model_performance (
    id            SERIAL PRIMARY KEY,
    model_name    VARCHAR(50) NOT NULL,
    location_id   INTEGER REFERENCES locations(id),
    variable      VARCHAR(50) NOT NULL,
    horizon_hours INTEGER NOT NULL,
    evaluated_at  TIMESTAMPTZ  DEFAULT NOW(),
    period_start  TIMESTAMPTZ,
    period_end    TIMESTAMPTZ,
    mae           DOUBLE PRECISION,
    rmse          DOUBLE PRECISION,
    r2            DOUBLE PRECISION,
    mape          DOUBLE PRECISION,
    sample_count  INTEGER
);
CREATE INDEX IF NOT EXISTS ix_perf_model_var ON model_performance (model_name, variable, horizon_hours);

-- ── Engineered features cache (optional, speeds up retraining) ─
CREATE TABLE IF NOT EXISTS engineered_features (
    id            SERIAL PRIMARY KEY,
    location_id   INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    timestamp     TIMESTAMPTZ NOT NULL,
    feature_data  JSONB,
    created_at    TIMESTAMPTZ  DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_feat_loc_time ON engineered_features (location_id, timestamp DESC);

-- ── Seed default Indian cities ────────────────────────────────
INSERT INTO locations (name, city, country, latitude, longitude, timezone) VALUES
  ('New Delhi',  'New Delhi',  'India',  28.6139,  77.2090, 'Asia/Kolkata'),
  ('Mumbai',     'Mumbai',     'India',  19.0760,  72.8777, 'Asia/Kolkata'),
  ('Bengaluru',  'Bengaluru',  'India',  12.9716,  77.5946, 'Asia/Kolkata'),
  ('Chennai',    'Chennai',    'India',  13.0827,  80.2707, 'Asia/Kolkata'),
  ('Kolkata',    'Kolkata',    'India',  22.5726,  88.3639, 'Asia/Kolkata'),
  ('Hyderabad',  'Hyderabad',  'India',  17.3850,  78.4867, 'Asia/Kolkata'),
  ('Pune',       'Pune',       'India',  18.5204,  73.8567, 'Asia/Kolkata'),
  ('Ahmedabad',  'Ahmedabad',  'India',  23.0225,  72.5714, 'Asia/Kolkata'),
  ('Jaipur',     'Jaipur',     'India',  26.9124,  75.7873, 'Asia/Kolkata'),
  ('Lucknow',    'Lucknow',    'India',  26.8467,  80.9462, 'Asia/Kolkata')
ON CONFLICT DO NOTHING;
