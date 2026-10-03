import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';
import { fmt, windDirection, weatherIcon } from '../utils/format';
import ConfidenceBadge from './ConfidenceBadge';

interface Props {
  points: ForecastPoint[];
  maxRows?: number;
}

export default function ForecastTable({ points, maxRows = 48 }: Props) {
  const rows = points.slice(0, maxRows);

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ background: 'var(--bg-elevated)' }}>
            {['Time', 'wx', 'Temp', 'Feels Like', 'Humid', 'Wind', 'Rain', 'Pressure', 'Confidence'].map(h => (
              <th key={h} style={{
                padding: '9px 12px', textAlign: 'left',
                fontWeight: 500, fontSize: '0.7rem',
                textTransform: 'uppercase', letterSpacing: '0.05em',
                color: 'var(--text-muted)',
                borderBottom: '1px solid var(--border)',
                whiteSpace: 'nowrap',
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((p, i) => (
            <tr key={i}
              style={{ borderBottom: '1px solid var(--border)', transition: 'background var(--transition)' }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <td style={{ padding: '9px 12px', whiteSpace: 'nowrap' }}>
                <div style={{ fontWeight: 600 }}>{format(parseISO(p.valid_time), 'HH:mm')}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {format(parseISO(p.valid_time), 'MMM d')}
                </div>
              </td>
              <td style={{ padding: '9px 12px', fontSize: '1.1rem' }}>
                {weatherIcon(p.temperature_c, p.precipitation_mm)}
              </td>
              <td style={{ padding: '9px 12px', fontWeight: 700, color: '#f97316' }}>
                {fmt.temp(p.temperature_c)}
              </td>
              <td style={{ padding: '9px 12px', color: 'var(--text-secondary)' }}>
                {p.temperature_c != null ? fmt.temp(p.temperature_c - 1.5) : '—'}
              </td>
              <td style={{ padding: '9px 12px', color: '#06b6d4' }}>
                {fmt.pct(p.humidity_pct)}
              </td>
              <td style={{ padding: '9px 12px', whiteSpace: 'nowrap' }}>
                <span style={{ fontWeight: 500 }}>{fmt.wind(p.wind_speed_kmh)}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.7rem', marginLeft: 4 }}>
                  {windDirection(p.wind_direction_deg)}
                </span>
              </td>
              <td style={{ padding: '9px 12px', color: '#3b82f6' }}>
                {fmt.mm(p.precipitation_mm)}
              </td>
              <td style={{ padding: '9px 12px', color: 'var(--text-muted)' }}>
                {fmt.hpa(p.pressure_hpa)}
              </td>
              <td style={{ padding: '9px 12px' }}>
                {p.uncertainty?.confidence_score != null ? (
                  <ConfidenceBadge score={p.uncertainty.confidence_score} size="sm" />
                ) : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
