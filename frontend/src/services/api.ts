/**
 * Frontend API service.
 * All requests go to /api (proxied to backend).
 * The Weather Union API key NEVER appears here — it lives only on the backend.
 */
import axios from 'axios';
import type {
  ForecastResponse,
  CurrentConditions,
  WeatherUnionStatus,
  Location,
  ModelPerformance,
  ModelComparisonSummary,
  HealthResponse,
  DynamicWeightsResponse,
  AblationResult,
} from '../types/weather';

const apiBase = import.meta.env.VITE_API_URL
  ? (import.meta.env.VITE_API_URL.endsWith('/api') ? import.meta.env.VITE_API_URL : `${import.meta.env.VITE_API_URL}/api`)
  : '/api';

const client = axios.create({
  baseURL: apiBase,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
});

// ── Forecast ────────────────────────────────────────────────────────
export const getForecastByCoords = async (
  lat: number,
  lon: number,
  hours: number = 48
): Promise<ForecastResponse> => {
  const { data } = await client.get('/forecast/', {
    params: { lat, lon, hours },
  });
  return data;
};

export const getForecastByLocation = async (
  locationId: number,
  hours: number = 48
): Promise<ForecastResponse> => {
  const { data } = await client.get(`/forecast/${locationId}`, {
    params: { hours },
  });
  return data;
};

// ── Current Conditions ──────────────────────────────────────────────
export const getCurrentConditions = async (
  lat: number,
  lon: number
): Promise<CurrentConditions> => {
  const { data } = await client.get('/weather/current', {
    params: { lat, lon },
  });
  return data;
};

// ── Weather Union Status ────────────────────────────────────────────
export const getWeatherUnionStatus = async (
  lat?: number,
  lon?: number
): Promise<WeatherUnionStatus> => {
  const { data } = await client.get('/weather/weather-union/status', {
    params: lat != null && lon != null ? { lat, lon } : {},
  });
  return data;
};

// ── Locations ───────────────────────────────────────────────────────
export const getLocations = async (): Promise<Location[]> => {
  const { data } = await client.get('/locations/');
  return data;
};

export const searchLocations = async (q: string): Promise<Location[]> => {
  const { data } = await client.get('/locations/search/', { params: { q } });
  return data;
};

export const createLocation = async (payload: {
  name: string;
  latitude: number;
  longitude: number;
  city?: string;
  country?: string;
}): Promise<Location> => {
  const { data } = await client.post('/locations/', payload);
  return data;
};

// ── Model Performance ───────────────────────────────────────────────
export const getModelPerformance = async (): Promise<ModelPerformance[]> => {
  const { data } = await client.get('/models/performance');
  return data;
};

export const getModelWeights = async (): Promise<DynamicWeightsResponse> => {
  const { data } = await client.get('/models/weights');
  return data;
};

export const getAblationResults = async (): Promise<AblationResult[]> => {
  const { data } = await client.get('/models/ablation');
  return data;
};

export const getModelComparison = async (): Promise<{
  models: ModelComparisonSummary[];
  message?: string;
  ablation?: AblationResult[];
}> => {
  const { data } = await client.get('/models/comparison');
  return data;
};

export const getMultiCityVerification = async (): Promise<{
  source: string;
  records: Array<{
    city: string;
    icao?: string;
    coords?: string;
    samples: number;
    nwp_mae: number;
    rf_mae: number;
    xgb_mae: number;
    ann_mae: number;
    best_model: string;
    skill_score_pct?: number;
  }>;
}> => {
  const { data } = await client.get('/models/verification');
  return data;
};

// ── Health ──────────────────────────────────────────────────────────
export const getHealth = async (): Promise<HealthResponse> => {
  const { data } = await client.get('/health');
  return data;
};
