import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';
import { fmt } from '../utils/format';

interface Props {
  points: ForecastPoint[];
  maxRows?: number;
}

const MODEL_COLS = [
  { key: 'gfs',    label: 'GFS',    color: '#06b6d4' },
  { key: 'ecmwf',  label: 'ECMWF',  color: '#3b82f6' },
  { key: 'jma',    label: 'JMA',    color: '#8b5cf6' },
];

export default function NWPComparisonTable({ points, maxRows = 24 }: Props) {
  const rows = points.slice(0, maxRows);

  return (
    <div style={{ overflowX: 'auto' }}>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
        <thead>
          <tr style={{ background: 'var(--bg-elevated)' }}>
            <th style={th}>Time</th>
            {MODEL_COLS.map(m => (
              <th key={m.key} style={{ ...th, color: m.color }}>{m.label} Temp</th>
            ))}
            <th style={{ ...th, color: '#f97316' }}>AI Ensemble</th>
            <th style={th}>Spread</th>
            <th style={th}>WU Correction</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((p, i) => {
            const gfsT  = p.gfs?.temperature_c;
            const ecmwfT = p.ecmwf?.temperature_c;
            const jmaT  = p.jma?.temperature_c;
            const vals = [gfsT, ecmwfT, jmaT].filter((v): v is number => v != null);
            const spread = vals.length > 1 ? Math.max(...vals) - Math.min(...vals) : null;
            const aiT = p.temperature_c;
            const nwpMean = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
            const wuCorr = aiT != null && nwpMean != null ? aiT - nwpMean : null;

            return (
              <tr key={i}
                style={{ borderBottom: '1px solid var(--border)', transition: 'background var(--transition)' }}
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={td}>{format(parseISO(p.valid_time), 'MMM d HH:mm')}</td>
                <td style={{ ...td, color: '#06b6d4', fontWeight: 500 }}>{fmt.temp(gfsT)}</td>
                <td style={{ ...td, color: '#3b82f6', fontWeight: 500 }}>{fmt.temp(ecmwfT)}</td>
                <td style={{ ...td, color: '#8b5cf6', fontWeight: 500 }}>{fmt.temp(jmaT)}</td>
                <td style={{ ...td, color: '#f97316', fontWeight: 700 }}>{fmt.temp(aiT)}</td>
                <td style={{ ...td, color: spread != null && spread > 2 ? 'var(--accent-yellow)' : 'var(--text-secondary)' }}>
                  {spread != null ? `${spread.toFixed(1)}°` : '—'}
                </td>
                <td style={{ ...td, color: wuCorr != null ? (wuCorr > 0 ? 'var(--accent-orange)' : 'var(--accent-cyan)') : 'var(--text-muted)' }}>
                  {wuCorr != null ? `${wuCorr > 0 ? '+' : ''}${wuCorr.toFixed(1)}°` : '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const th: React.CSSProperties = {
  padding: '9px 12px', textAlign: 'left',
  fontWeight: 500, fontSize: '0.72rem',
  textTransform: 'uppercase', letterSpacing: '0.05em',
  color: 'var(--text-muted)',
  borderBottom: '1px solid var(--border)',
};
const td: React.CSSProperties = {
  padding: '9px 12px',
  color: 'var(--text-primary)',
};
