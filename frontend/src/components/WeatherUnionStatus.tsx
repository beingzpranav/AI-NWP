import { Wifi, WifiOff, AlertCircle } from 'lucide-react';
import { useWeatherUnionStatus } from '../hooks/useWeather';
import { fmt } from '../utils/format';

interface Props { lat: number; lon: number; }

export default function WeatherUnionStatus({ lat, lon }: Props) {
  const { data: status, isLoading } = useWeatherUnionStatus(lat, lon);

  if (isLoading) {
    return (
      <div className="card" style={{ padding: 16 }}>
        <div className="skeleton" style={{ height: 60, borderRadius: 8 }} />
      </div>
    );
  }

  const isConnected = status?.connected;
  const isConfigured = status?.configured;

  return (
    <div className="card" style={{
      padding: 16,
      borderLeft: `3px solid ${
        isConnected ? 'var(--accent-cyan)' :
        isConfigured ? 'var(--accent-yellow)' : 'var(--accent-red)'
      }`,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <div style={{
          width: 40, height: 40, borderRadius: 10,
          background: isConnected
            ? 'rgba(6,182,212,0.15)'
            : isConfigured ? 'rgba(234,179,8,0.15)' : 'rgba(239,68,68,0.15)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          {isConnected
            ? <Wifi size={18} color="var(--accent-cyan)" />
            : isConfigured
              ? <AlertCircle size={18} color="var(--accent-yellow)" />
              : <WifiOff size={18} color="var(--accent-red)" />
          }
        </div>

        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
            <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Weather Union</span>
            <span className={`badge ${
              isConnected ? 'badge-cyan' : isConfigured ? 'badge-yellow' : 'badge-red'
            }`}>
              {isConnected ? 'Live' : isConfigured ? 'No Data' : 'Not Configured'}
            </span>
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            {status?.message}
          </div>
          {status?.last_observation_at && (
            <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', marginTop: 2 }}>
              Last obs: {fmt.datetime(status.last_observation_at)}
            </div>
          )}
        </div>

        {status?.station_count != null && status.station_count > 0 && (
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '1.4rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
              {status.station_count}
            </div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>stations</div>
          </div>
        )}
      </div>

      {!isConfigured && (
        <div style={{
          marginTop: 12, padding: '8px 12px',
          background: 'rgba(239,68,68,0.08)', borderRadius: 8,
          fontSize: '0.78rem', color: 'var(--text-secondary)',
        }}>
          Set <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>
            WEATHER_UNION_API_KEY
          </code> in <code style={{ fontFamily: 'var(--font-mono)' }}>backend/.env</code> to enable local observations.
        </div>
      )}
    </div>
  );
}
