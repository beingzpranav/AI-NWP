-- Weather AI Platform — Initial Database Migration
-- Run via: psql -U weather_user -d weather_ai_db -f 001_initial.sql

-- Extension for better timestamp handling
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Locations
CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'India',
    latitude FLOAT NOT NULL,
    longitude FLOAT NOT NULL,
    elevation_m FLOAT,
    timezone VARCHAR(50) DEFAULT 'Asia/Kolkata',
    weather_union_station_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_locations_lat_lon ON locations(latitude, longitude);
CREATE INDEX IF NOT EXISTS ix_locations_city ON locations(city);

-- Historical weather observations
CREATE TABLE IF NOT EXISTS weather_observations (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    observed_at TIMESTAMPTZ NOT NULL,
    temperature_c FLOAT,
    feels_like_c FLOAT,
    humidity_pct FLOAT,
    pressure_hpa FLOAT,
    wind_speed_ms FLOAT,
    wind_direction_deg FLOAT,
    precipitation_mm FLOAT,
    visibility_km FLOAT,
    solar_radiation_wm2 FLOAT,
    dew_point_c FLOAT,
    cloud_cover_pct FLOAT,
    uv_index FLOAT,
    source VARCHAR(50) DEFAULT 'historical',
    quality_flag BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_obs_location_time ON weather_observations(location_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_obs_observed_at ON weather_observations(observed_at);

-- Weather Union observations
CREATE TABLE IF NOT EXISTS weather_union_observations (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    station_id VARCHAR(100) NOT NULL,
    station_name VARCHAR(200),
    observed_at TIMESTAMPTZ NOT NULL,
    temperature_c FLOAT,
    humidity_pct FLOAT,
    pressure_hpa FLOAT,
    wind_speed_ms FLOAT,
    wind_direction_deg FLOAT,
    precipitation_mm FLOAT,
    rain_intensity_mmph FLOAT,
    light_intensity_lux FLOAT,
    temp_bias_gfs FLOAT,
    temp_bias_ecmwf FLOAT,
    temp_bias_jma FLOAT,
    humidity_bias_gfs FLOAT,
    humidity_bias_ecmwf FLOAT,
    humidity_bias_jma FLOAT,
    pressure_bias_gfs FLOAT,
    pressure_bias_ecmwf FLOAT,
    pressure_bias_jma FLOAT,
    wind_bias_gfs FLOAT,
    wind_bias_ecmwf FLOAT,
    wind_bias_jma FLOAT,
    raw_payload VARCHAR(2000),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_wu_station_time ON weather_union_observations(station_id, observed_at);
CREATE INDEX IF NOT EXISTS ix_wu_location_time ON weather_union_observations(location_id, observed_at);

-- NWP forecasts
CREATE TABLE IF NOT EXISTS nwp_forecasts (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    model_name VARCHAR(50) NOT NULL,
    run_time TIMESTAMPTZ NOT NULL,
    valid_time TIMESTAMPTZ NOT NULL,
    horizon_h INTEGER NOT NULL,
    temperature_c FLOAT,
    humidity_pct FLOAT,
    pressure_hpa FLOAT,
    wind_speed_ms FLOAT,
    wind_direction_deg FLOAT,
    precipitation_mm FLOAT,
    cloud_cover_pct FLOAT,
    dew_point_c FLOAT,
    visibility_km FLOAT,
    solar_radiation_wm2 FLOAT,
    wind_gusts_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_nwp_location_model_valid ON nwp_forecasts(location_id, model_name, valid_time);
CREATE INDEX IF NOT EXISTS ix_nwp_valid_time ON nwp_forecasts(valid_time);

-- Forecast runs
CREATE TABLE IF NOT EXISTS forecast_runs (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    run_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    model_version VARCHAR(100),
    gfs_available INTEGER DEFAULT 0,
    ecmwf_available INTEGER DEFAULT 0,
    jma_available INTEGER DEFAULT 0,
    weather_union_available INTEGER DEFAULT 0,
    model_weights JSONB,
    error_message VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_forecast_runs_location_time ON forecast_runs(location_id, run_at);

-- Model predictions
CREATE TABLE IF NOT EXISTS model_predictions (
    id SERIAL PRIMARY KEY,
    forecast_run_id INTEGER REFERENCES forecast_runs(id),
    location_id INTEGER REFERENCES locations(id),
    valid_time TIMESTAMPTZ NOT NULL,
    horizon_h INTEGER NOT NULL,
    temperature_c FLOAT,
    humidity_pct FLOAT,
    pressure_hpa FLOAT,
    wind_speed_ms FLOAT,
    wind_direction_deg FLOAT,
    precipitation_mm FLOAT,
    temperature_uncertainty FLOAT,
    humidity_uncertainty FLOAT,
    pressure_uncertainty FLOAT,
    wind_speed_uncertainty FLOAT,
    precipitation_uncertainty FLOAT,
    overall_confidence FLOAT,
    gfs_temperature FLOAT,
    ecmwf_temperature FLOAT,
    jma_temperature FLOAT,
    rf_temperature FLOAT,
    xgb_temperature FLOAT,
    ada_temperature FLOAT,
    ensemble_temperature FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_predictions_location_valid ON model_predictions(location_id, valid_time);

-- Model performance
CREATE TABLE IF NOT EXISTS model_performance (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    model_name VARCHAR(100) NOT NULL,
    target_variable VARCHAR(100) NOT NULL,
    horizon_h INTEGER NOT NULL,
    evaluated_at TIMESTAMPTZ NOT NULL,
    window_days INTEGER DEFAULT 7,
    mae FLOAT,
    rmse FLOAT,
    mape FLOAT,
    r2 FLOAT,
    n_samples INTEGER DEFAULT 0,
    reliability_score FLOAT,
    dynamic_weight FLOAT
);
CREATE INDEX IF NOT EXISTS ix_perf_location_model_time ON model_performance(location_id, model_name, evaluated_at);

-- Engineered features cache
CREATE TABLE IF NOT EXISTS engineered_features (
    id SERIAL PRIMARY KEY,
    location_id INTEGER REFERENCES locations(id),
    feature_time TIMESTAMPTZ NOT NULL,
    feature_vector JSONB NOT NULL,
    feature_version VARCHAR(20) DEFAULT '1.0',
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_features_location_time ON engineered_features(location_id, feature_time);
