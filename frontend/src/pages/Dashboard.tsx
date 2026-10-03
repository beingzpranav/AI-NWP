import { useState } from 'react';
import { Thermometer, Droplets, Wind, Gauge, CloudRain, Eye, MapPin, RefreshCw, Compass, ShieldCheck } from 'lucide-react';
import MetricCard from '../components/MetricCard';
import WeatherUnionStatus from '../components/WeatherUnionStatus';
import ModelWeightsDisplay from '../components/ModelWeightsDisplay';
import LocationSearch from '../components/LocationSearch';
import ConfidenceBadge from '../components/ConfidenceBadge';
import ForecastChart from '../charts/ForecastChart';
import ConfidenceChart from '../charts/ConfidenceChart';
import { useForecast, useCurrentConditions } from '../hooks/useWeather';
import { useLocationState } from '../hooks/useLocation';
import { fmt, windDirection, weatherIcon } from '../utils/format';
import ErrorState from '../components/ErrorState';

type ChartVar = 'temperature_c' | 'humidity_pct' | 'wind_speed_kmh' | 'precipitation_mm';

const CHART_TABS: { key: ChartVar; label: string }[] = [
  { key: 'temperature_c',    label: 'Temperature' },
  { key: 'humidity_pct',     label: 'Humidity' },
  { key: 'wind_speed_kmh',   label: 'Wind' },
  { key: 'precipitation_mm', label: 'Rain' },
];

export default function Dashboard() {
  const { coords, setLocation } = useLocationState();
  const [chartVar, setChartVar] = useState<ChartVar>('temperature_c');

  const { data: current, isLoading: currentLoading, error: currentError, refetch: refetchCurrent } =
    useCurrentConditions(coords.lat, coords.lon);
  const { data: forecast, isLoading: forecastLoading, refetch: refetchForecast } =
    useForecast(coords.lat, coords.lon, 48);

  const currentPoint = forecast?.points?.[0];
  const cityWeights = currentPoint?.weights ?? null;
  const wuActualTemp = current?.weather_union_temp ?? current?.temperature_c ?? null;
  const wuActualTime = currentPoint?.valid_time ?? null;
  const isLoading = currentLoading || forecastLoading;

  // Dew point approximation: Td = T - ((100 - RH)/5)
  const tempVal = current?.temperature_c ?? currentPoint?.temperature_c ?? 0;
  const rhVal = current?.humidity_pct ?? currentPoint?.humidity_pct ?? 50;
  const dewPointVal = tempVal - ((100 - rhVal) / 5);

  return (
    <div style={{ padding: '24px', maxWidth: 1400, margin: '0 auto' }}>

      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 260 }}>
          <LocationSearch onSelect={(lat, lon, label) => setLocation(lat, lon, label)} />
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MapPin size={14} color="var(--text-muted)" />
          <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            {coords.label} · {coords.lat.toFixed(3)}°N, {coords.lon.toFixed(3)}°E
          </span>
          <span className="badge badge-blue" style={{ fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
            SYNOPTIC OBS
          </span>
        </div>
        <button
          onClick={() => { refetchCurrent(); refetchForecast(); }}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '7px 14px', background: 'var(--bg-elevated)',
            border: '1px solid var(--border)', borderRadius: 8,
            color: 'var(--text-secondary)', fontSize: '0.8rem',
            cursor: 'pointer', transition: 'all var(--transition)',
          }}
        >
          <RefreshCw size={13} />
          Refresh
        </button>
      </div>

      {/* Hero current conditions */}
      <div className="card" style={{
        padding: 28, marginBottom: 20,
        background: 'linear-gradient(135deg, var(--bg-card) 0%, var(--bg-elevated) 100%)',
        position: 'relative', overflow: 'hidden',
      }}>
        {/* Background glow */}
        <div style={{
          position: 'absolute', top: -60, right: -60,
          width: 240, height: 240, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)',
          pointerEvents: 'none',
        }} />

        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 32, flexWrap: 'wrap' }}>
          {/* Big temp */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Operational MOS Forecast Temperature
              </span>
              <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>MOS Corrected</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: '5rem', fontWeight: 800, lineHeight: 1,
                             background: 'linear-gradient(135deg, #f97316, #ef4444)',
                             WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                {currentLoading ? '—' : fmt.temp(current?.temperature_c ?? currentPoint?.temperature_c).replace('°C', '')}
              </span>
              <span style={{ fontSize: '2rem', color: 'var(--text-secondary)', fontWeight: 300 }}>°C</span>
            </div>
            {current?.feels_like_c != null && (
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: 4 }}>
                Feels like {fmt.temp(current.feels_like_c)} · Dew Point: <strong style={{ color: '#06b6d4' }}>{dewPointVal.toFixed(1)}°C</strong>
              </div>
            )}
            <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: '2rem' }}>
                {weatherIcon(current?.temperature_c, current?.precipitation_mm)}
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                {current?.source ?? 'NWP Ensemble MOS'}
              </span>
              {currentPoint?.uncertainty && (
                <ConfidenceBadge score={currentPoint.uncertainty.confidence_score} size="sm" />
              )}
            </div>
          </div>

          {/* Details grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, flex: 1, minWidth: 300 }}>
            <MetricCard
              label="Humidity / DewPt" loading={isLoading}
              value={fmt.pct(current?.humidity_pct ?? currentPoint?.humidity_pct)}
              subValue={`Dew Point ${dewPointVal.toFixed(1)}°C`}
              icon={<Droplets size={16} />} color="var(--accent-cyan)"
            />
            <MetricCard
              label="Sea-Level Pressure" loading={isLoading}
              value={fmt.hpa(current?.pressure_hpa ?? currentPoint?.pressure_hpa)}
              subValue="Barometric QNH"
              icon={<Gauge size={16} />} color="var(--accent-purple)"
            />
            <MetricCard
              label="Wind Vector" loading={isLoading}
              value={fmt.wind(current?.wind_speed_kmh ?? currentPoint?.wind_speed_kmh)}
              subValue={windDirection(current?.wind_direction_deg ?? currentPoint?.wind_direction_deg)}
              icon={<Wind size={16} />} color="var(--accent-blue)"
            />
            <MetricCard
              label="Rainfall Rate" loading={isLoading}
              value={fmt.mm(current?.precipitation_mm ?? currentPoint?.precipitation_mm)}
              subValue="Surface Accumulation"
              icon={<CloudRain size={16} />} color="var(--accent-blue)"
            />
            <MetricCard
              label="Active NWP Models" loading={isLoading}
              value={forecast ? String(Object.values(forecast.data_sources).filter(Boolean).length) + ' / 4' : '—'}
              subValue="GFS · ECMWF · JMA · ML"
              icon={<Eye size={16} />} color="var(--accent-green)"
            />
            {current?.weather_union_available && (
              <MetricCard
                label="Station Truth Obs" loading={false}
                value={fmt.temp(current.weather_union_temp)}
                subValue={current.weather_union_station ?? 'METAR Station'}
                icon={<Thermometer size={16} />} color="var(--accent-cyan)"
              />
            )}
          </div>
        </div>
      </div>

      {/* Data sources row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: 20, marginBottom: 20 }}>
        {/* NWP source pills */}
        <div className="card" style={{ padding: 16 }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 12,
                        textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            NWP Global Numerical Data Stream & Ingestion
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {forecast && Object.entries(forecast.data_sources).map(([src, available]) => (
              <span key={src} className={`badge ${available ? 'badge-green' : 'badge-red'}`}>
                {available ? '✓ ACTIVE' : '✗ OFFLINE'} {src.toUpperCase()}
              </span>
            ))}
          </div>
        </div>
        {/* Model weights */}
        <ModelWeightsDisplay overrideWeights={cityWeights} />
      </div>

      {/* Forecast chart */}
      <div className="card" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <div style={{ fontWeight: 600, marginBottom: 2 }}>48-Hour Ensemble Forecast & Ground Truth Verification</div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              AI MOS Residual Corrected · GFS (0.25°) + ECMWF (0.1°) + JMA GSM + METAR Ground Truth
            </div>
          </div>
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg-elevated)',
                        padding: 4, borderRadius: 10 }}>
            {CHART_TABS.map(tab => (
              <button key={tab.key} onClick={() => setChartVar(tab.key)}
                style={{
                  padding: '5px 12px', borderRadius: 7, border: 'none',
                  fontSize: '0.78rem', fontWeight: 500, cursor: 'pointer',
                  background: chartVar === tab.key ? 'var(--accent-blue)' : 'transparent',
                  color: chartVar === tab.key ? '#fff' : 'var(--text-secondary)',
                  transition: 'all var(--transition)',
                }}>
                {tab.label}
              </button>
            ))}
          </div>
        </div>
        {isLoading ? <div className="skeleton" style={{ height: 300, borderRadius: 8 }} /> :
         currentError ? <ErrorState title="Current weather unavailable" onRetry={() => refetchCurrent()} /> :
         <ForecastChart points={forecast?.points ?? []} variable={chartVar}
           wuActualTemp={chartVar === 'temperature_c' ? wuActualTemp : null}
           wuActualTime={wuActualTime} />}
      </div>

      {/* Weather union station widget */}
      <WeatherUnionStatus lat={coords.lat} lon={coords.lon} />
    </div>
  );
}
