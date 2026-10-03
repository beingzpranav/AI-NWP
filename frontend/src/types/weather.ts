export interface Location {
  id: number;
  name: string;
  city?: string;
  country?: string;
  latitude: number;
  longitude: number;
  elevation_m?: number;
  timezone: string;
  is_active: boolean;
  created_at: string;
}

export interface UncertaintyBands {
  temperature_sigma?: number;
  humidity_sigma?: number;
  wind_speed_sigma?: number;
  precipitation_sigma?: number;
  confidence_score: number;
}

export interface ModelWeights {
  gfs: number;
  ecmwf: number;
  jma: number;
  ml: number;
}

export interface NWPForecastPoint {
  model_name: string;
  valid_time: string;
  horizon_hours: number;
  temperature_c?: number;
  humidity_pct?: number;
  wind_speed_kmh?: number;
  precipitation_mm?: number;
  pressure_hpa?: number;
}

export interface ForecastPoint {
  valid_time: string;
  horizon_hours: number;
  temperature_c?: number;
  actual_temperature_c?: number | null;
  humidity_pct?: number;
  wind_speed_kmh?: number;
  wind_direction_deg?: number;
  precipitation_mm?: number;
  pressure_hpa?: number;
  uncertainty?: UncertaintyBands;
  gfs?: NWPForecastPoint;
  ecmwf?: NWPForecastPoint;
  jma?: NWPForecastPoint;
  weights?: ModelWeights;
}

export interface ForecastResponse {
  location: Location;
  generated_at: string;
  forecast_hours: number;
  data_sources: Record<string, boolean>;
  points: ForecastPoint[];
}

export interface CurrentConditions {
  location: Location;
  observed_at: string;
  source: string;
  temperature_c?: number;
  feels_like_c?: number;
  humidity_pct?: number;
  pressure_hpa?: number;
  wind_speed_kmh?: number;
  wind_direction_deg?: number;
  precipitation_mm?: number;
  visibility_m?: number;
  weather_union_available: boolean;
  weather_union_temp?: number;
  weather_union_station?: string;
}

export interface WeatherUnionStatus {
  configured: boolean;
  connected: boolean;
  last_observation_at?: string;
  station_count: number;
  message: string;
}

export interface ModelPerformance {
  model_name: string;
  variable: string;
  horizon_hours: number;
  mae?: number;
  rmse?: number;
  r2?: number;
  mape?: number;
  sample_count?: number;
  evaluated_at: string;
}

export interface ModelComparisonSummary {
  model: string;
  avg_mae?: number;
  avg_rmse?: number;
  avg_r2?: number;
  n_evaluations: number;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  app: string;
  environment: string;
  weather_union_configured: boolean;
}

export interface DynamicWeightsResponse {
  weights: Record<string, number>;
  computed_at?: string;
  method?: string;
  note?: string;
  sum?: number;
}

export interface AblationResult {
  experiment: string;
  model: string;
  variable: string;
  horizon_hours: number;
  mae?: number;
  rmse?: number;
  r2?: number;
  mape?: number;
  sample_count?: number;
  absolute_improvement_vs_baseline?: number;
  percent_improvement_vs_baseline?: number;
  absolute_improvement?: number;
  percentage_improvement?: number;
  baseline_error?: number;
  new_error?: number;
}

