import { useState } from 'react';
import { Clock, Calendar, TrendingUp, AlertTriangle, ShieldCheck } from 'lucide-react';
import LocationSearch from '../components/LocationSearch';
import ForecastChart from '../charts/ForecastChart';
import ConfidenceChart from '../charts/ConfidenceChart';
import ConfidenceBadge from '../components/ConfidenceBadge';
import LoadingState from '../components/LoadingState';
import ErrorState from '../components/ErrorState';
import { useForecast, useCurrentConditions } from '../hooks/useWeather';
import { useLocationState } from '../hooks/useLocation';
import { fmt, windDirection, weatherIcon } from '../utils/format';
import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';

type HorizonTab = '24h' | '48h' | '7d';
type ChartVar = 'temperature_c' | 'humidity_pct' | 'wind_speed_kmh' | 'precipitation_mm';

const CHART_VARS: { key: ChartVar; label: string; color: string }[] = [
  { key: 'temperature_c',    label: 'Temp',   color: '#f97316' },
  { key: 'humidity_pct',     label: 'Humid',  color: '#06b6d4' },
  { key: 'wind_speed_kmh',   label: 'Wind',   color: '#8b5cf6' },
  { key: 'precipitation_mm', label: 'Rain',   color: '#3b82f6' },
];

function HourlyRow({ point }: { point: ForecastPoint }) {
  const hour = format(parseISO(point.valid_time), 'HH:mm');
  const date = format(parseISO(point.valid_time), 'MMM d');
  const conf = point.uncertainty?.confidence_score ?? 0;
  const std = point.uncertainty?.temperature_sigma ?? 0.8;

  // Dew point approximation: Td = T - ((100 - RH)/5)
  const temp = point.temperature_c ?? 0;
  const rh = point.humidity_pct ?? 50;
  const dewPoint = temp - ((100 - rh) / 5);

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '80px 50px 75px 75px 75px 85px 75px 75px 95px 1fr',
      gap: 8, alignItems: 'center',
      padding: '10px 16px',
      borderBottom: '1px solid var(--border)',
      fontSize: '0.82rem',
      transition: 'background var(--transition)',
    }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <div>
        <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{hour}</div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{date}</div>
      </div>
      <div style={{ fontSize: '1.2rem' }}>{weatherIcon(point.temperature_c, point.precipitation_mm)}</div>
      <div style={{ fontWeight: 700, color: '#f97316' }}>{fmt.temp(point.temperature_c)}</div>
      <div style={{ color: '#06b6d4', fontSize: '0.78rem' }}>Td {dewPoint.toFixed(1)}°C</div>
      <div style={{ color: 'var(--text-secondary)' }}>{fmt.pct(point.humidity_pct)}</div>
      <div style={{ color: 'var(--text-secondary)' }}>
        {fmt.wind(point.wind_speed_kmh)}
        <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginLeft: 4 }}>
          {windDirection(point.wind_direction_deg)}
        </span>
      </div>
      <div style={{ color: 'var(--accent-blue)' }}>{fmt.mm(point.precipitation_mm)}</div>
      <div style={{ color: 'var(--text-secondary)' }}>{fmt.hpa(point.pressure_hpa)}</div>
      <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
        ±{(1.96 * std).toFixed(1)}°C
      </div>
      <ConfidenceBadge score={conf} size="sm" />
    </div>
  );
}

function NWPRow({ point }: { point: ForecastPoint }) {
  const gfs = point.gfs?.temperature_c;
  const ecmwf = point.ecmwf?.temperature_c;
  const jma = point.jma?.temperature_c;
  const temps = [gfs, ecmwf, jma].filter((t): t is number => t != null);
  
  const mean = temps.length ? temps.reduce((a, b) => a + b, 0) / temps.length : 0;
  const spread = temps.length > 1 
    ? Math.sqrt(temps.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / temps.length)
    : 0;

  const isDivergent = spread > 1.2;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '80px 1fr 1fr 1fr 1fr 1fr 1fr',
      gap: 8, alignItems: 'center',
      padding: '9px 16px',
      borderBottom: '1px solid var(--border)',
      fontSize: '0.82rem',
    }}
      onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
      onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
    >
      <div style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
        {format(parseISO(point.valid_time), 'HH:mm')}
      </div>
      <div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 2 }}>GFS 0.25°</div>
        <div style={{ color: '#06b6d4', fontWeight: 600 }}>{fmt.temp(gfs)}</div>
      </div>
      <div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 2 }}>ECMWF 0.1°</div>
        <div style={{ color: '#3b82f6', fontWeight: 600 }}>{fmt.temp(ecmwf)}</div>
      </div>
      <div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 2 }}>JMA GSM</div>
        <div style={{ color: '#8b5cf6', fontWeight: 600 }}>{fmt.temp(jma)}</div>
      </div>
      <div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 2 }}>NWP Spread σ</div>
        <div style={{ color: isDivergent ? '#ef4444' : '#22c55e', fontWeight: 700 }}>
          {spread > 0 ? `±${spread.toFixed(2)}°C` : '—'}
        </div>
      </div>
      <div>
        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 2 }}>AI MOS Ensemble</div>
        <div style={{ color: '#f97316', fontWeight: 800 }}>{fmt.temp(point.temperature_c)}</div>
      </div>
      <div>
        {isDivergent ? (
          <span className="badge badge-yellow" style={{ fontSize: '0.65rem' }}>High Spread</span>
        ) : (
          <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>Low Spread</span>
        )}
      </div>
    </div>
  );
}

export default function ForecastPage() {
  const { coords, setLocation } = useLocationState();
  const [horizon, setHorizon] = useState<HorizonTab>('48h');
  const [chartVar, setChartVar] = useState<ChartVar>('temperature_c');
  const [activeTab, setActiveTab] = useState<'hourly' | 'nwp'>('hourly');

  const hours = horizon === '24h' ? 24 : horizon === '48h' ? 48 : 168;
  const { data: forecast, isLoading, error, refetch } = useForecast(coords.lat, coords.lon, hours);
  const { data: current } = useCurrentConditions(coords.lat, coords.lon);

  const points = forecast?.points ?? [];
  const wuActualTemp = current?.weather_union_temp ?? current?.temperature_c ?? null;
  const wuActualTime = points[0]?.valid_time ?? null;

  const horizonBtns: HorizonTab[] = ['24h', '48h', '7d'];

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>

      {/* Page header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 24, flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>
            <TrendingUp size={20} style={{ marginRight: 8, verticalAlign: 'middle', color: 'var(--accent-blue)' }} />
            Synoptic Forecast & NWP Ensemble Explorer
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Multi-model NWP Ensemble (GFS 0.25° · ECMWF 0.1° · JMA GSM) + Model Output Statistics (MOS) AI Residual Engine
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <div style={{ minWidth: 240 }}>
            <LocationSearch onSelect={(lat, lon, label) => setLocation(lat, lon, label)} />
          </div>
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg-elevated)', padding: 4, borderRadius: 10 }}>
            {horizonBtns.map(h => (
              <button key={h} onClick={() => setHorizon(h)} style={{
                padding: '5px 14px', borderRadius: 7, border: 'none', cursor: 'pointer',
                fontSize: '0.8rem', fontWeight: 500,
                background: horizon === h ? 'var(--accent-blue)' : 'transparent',
                color: horizon === h ? '#fff' : 'var(--text-secondary)',
                transition: 'all var(--transition)',
              }}>{h}</button>
            ))}
          </div>
        </div>
      </div>

      {/* Chart section */}
      <div className="card" style={{ padding: 24, marginBottom: 20 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
          <div style={{ fontWeight: 600 }}>Forecast vs Multi-Model NWP Baselines</div>
          <div style={{ display: 'flex', gap: 4, background: 'var(--bg-elevated)', padding: 3, borderRadius: 8 }}>
            {CHART_VARS.map(v => (
              <button key={v.key} onClick={() => setChartVar(v.key)} style={{
                padding: '4px 12px', borderRadius: 6, border: 'none', cursor: 'pointer',
                fontSize: '0.75rem', fontWeight: 500,
                background: chartVar === v.key ? v.color : 'transparent',
                color: chartVar === v.key ? '#fff' : 'var(--text-secondary)',
                transition: 'all var(--transition)',
              }}>{v.label}</button>
            ))}
          </div>
        </div>
        {isLoading ? <div className="skeleton" style={{ height: 300, borderRadius: 8 }} /> :
         error ? <ErrorState title="Forecast unavailable" onRetry={() => refetch()} /> :
         <ForecastChart points={points} variable={chartVar}
           wuActualTemp={chartVar === 'temperature_c' ? wuActualTemp : null}
           wuActualTime={wuActualTime} />}
      </div>

      {/* Two column: confidence + summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 20, marginBottom: 20 }}>
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Epistemic & Aleatoric Uncertainty Bounds</div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 16 }}>
            Heteroscedastic Gaussian NLL log-variance (σ²) output from PyTorch Two-Head ANN architecture
          </div>
          {isLoading ? <div className="skeleton" style={{ height: 180 }} /> :
           <ConfidenceChart points={points.slice(0, 24)} />}
        </div>

        <div className="card" style={{ padding: 20 }}>
          <div style={{ fontWeight: 600, marginBottom: 16 }}>Synoptic Horizon Summary</div>
          {isLoading ? <div className="skeleton" style={{ height: 160 }} /> : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[
                { label: 'Max Temperature', value: fmt.temp(Math.max(...points.filter(p => p.temperature_c != null).map(p => p.temperature_c!))), color: '#f97316' },
                { label: 'Min Temperature', value: fmt.temp(Math.min(...points.filter(p => p.temperature_c != null).map(p => p.temperature_c!))), color: '#06b6d4' },
                { label: 'Max Wind Velocity', value: fmt.wind(Math.max(...points.filter(p => p.wind_speed_kmh != null).map(p => p.wind_speed_kmh!))), color: '#8b5cf6' },
                { label: 'Accumulated Rain', value: fmt.mm(points.reduce((s, p) => s + (p.precipitation_mm ?? 0), 0)), color: '#3b82f6' },
                { label: 'Avg Skill Confidence', value: fmt.pct2(points.reduce((s, p) => s + (p.uncertainty?.confidence_score ?? 0), 0) / Math.max(points.length, 1)), color: '#22c55e' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{label}</span>
                  <span style={{ fontWeight: 700, color }}>{value}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Table section */}
      <div className="card" style={{ overflow: 'hidden' }}>
        <div style={{
          display: 'flex', gap: 0, borderBottom: '1px solid var(--border)',
          padding: '0 16px', background: 'var(--bg-elevated)',
        }}>
          {(['hourly', 'nwp'] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)} style={{
              padding: '14px 20px', border: 'none', background: 'none', cursor: 'pointer',
              fontSize: '0.85rem', fontWeight: 600,
              color: activeTab === tab ? 'var(--text-accent)' : 'var(--text-muted)',
              borderBottom: activeTab === tab ? '2px solid var(--accent-blue)' : '2px solid transparent',
              transition: 'all var(--transition)', marginBottom: -1,
            }}>
              {tab === 'hourly' ? '⏱ Synoptic Hourly Detail (Dew Point & Confidence)' : '🌐 Multi-Model NWP Spread Comparison'}
            </button>
          ))}
        </div>

        {activeTab === 'hourly' ? (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '80px 50px 75px 75px 75px 85px 75px 75px 95px 1fr',
              gap: 8, padding: '8px 16px',
              fontSize: '0.7rem', color: 'var(--text-muted)',
              textTransform: 'uppercase', letterSpacing: '0.05em',
              borderBottom: '1px solid var(--border)',
              background: 'var(--bg-elevated)',
            }}>
              <div>Valid Time</div><div>wx</div><div>Temp</div>
              <div>Dew Point</div><div>Humid</div><div>Wind</div><div>Rain</div>
              <div>SLP (hPa)</div><div>95% CI (±1.96σ)</div><div>Confidence</div>
            </div>
            <div style={{ maxHeight: 420, overflowY: 'auto' }}>
              {isLoading ? <LoadingState /> :
               points.slice(0, hours).map((p, i) => <HourlyRow key={i} point={p} />)}
            </div>
          </>
        ) : (
          <>
            <div style={{
              display: 'grid',
              gridTemplateColumns: '80px 1fr 1fr 1fr 1fr 1fr 1fr',
              gap: 8, padding: '8px 16px',
              fontSize: '0.7rem', color: 'var(--text-muted)',
              textTransform: 'uppercase', letterSpacing: '0.05em',
              borderBottom: '1px solid var(--border)',
              background: 'var(--bg-elevated)',
            }}>
              <div>Valid Time</div><div>GFS 0.25°</div><div>ECMWF 0.1°</div><div>JMA GSM</div><div>Ensemble Spread σ</div><div>AI MOS Ensemble</div><div>Spread Flag</div>
            </div>
            <div style={{ maxHeight: 420, overflowY: 'auto' }}>
              {isLoading ? <LoadingState /> :
               points.slice(0, 48).map((p, i) => <NWPRow key={i} point={p} />)}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
