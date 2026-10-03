import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceDot,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';

interface Props {
  points: ForecastPoint[];
  variable?: 'temperature_c' | 'humidity_pct' | 'wind_speed_kmh' | 'precipitation_mm';
  wuActualTemp?: number | null;
  wuActualTime?: string | null;
}

const VAR_CONFIG = {
  temperature_c:    { label: 'Temperature (°C)', color: '#f97316', unit: '°C' },
  humidity_pct:     { label: 'Humidity (%)',      color: '#06b6d4', unit: '%' },
  wind_speed_kmh:   { label: 'Wind (km/h)',       color: '#8b5cf6', unit: 'km/h' },
  precipitation_mm: { label: 'Precipitation (mm)', color: '#3b82f6', unit: 'mm' },
};

const CustomTooltip = ({ active, payload, label, unit }: any) => {
  if (!active || !payload?.length) return null;
  const filtered = payload.filter((p: any) =>
    p.dataKey !== 'upper' && p.dataKey !== 'lower' && p.name !== ''
  );
  return (
    <div style={{
      background: 'rgba(15, 23, 42, 0.95)', border: '1px solid var(--border)',
      borderRadius: 10, padding: '10px 14px', boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      fontSize: '0.8rem', backdropFilter: 'blur(8px)',
    }}>
      <div style={{ color: '#94a3b8', marginBottom: 6, fontWeight: 600 }}>{label}</div>
      {filtered.map((p: any) => (
        <div key={p.dataKey} style={{
          display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4
        }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: p.color }} />
          <span style={{ color: '#cbd5e1' }}>{p.name}:</span>
          <span style={{ fontWeight: 700, color: p.color }}>
            {typeof p.value === 'number' ? `${p.value.toFixed(1)} ${unit}` : '—'}
          </span>
        </div>
      ))}
    </div>
  );
};

const WUDotLabel = ({ viewBox, value, unit }: any) => {
  if (!viewBox) return null;
  const { cx, cy } = viewBox;
  return (
    <g>
      <rect x={cx - 35} y={cy - 25} width={70} height={18} rx={4} fill="#10b981" />
      <text x={cx} y={cy - 12} fill="#ffffff" fontSize={10} fontWeight={800} textAnchor="middle">
        OBS {value?.toFixed(1)}{unit}
      </text>
    </g>
  );
};

export default function ForecastChart({ points, variable = 'temperature_c', wuActualTemp, wuActualTime }: Props) {
  const cfg = VAR_CONFIG[variable];

  const data = points.map(p => {
    const act = (p as any).actual_temperature_c ?? (p.horizon_hours === 0 && wuActualTemp != null ? wuActualTemp : null);
    const val = p[variable] ?? null;
    const sigma = p.uncertainty?.temperature_sigma ?? 0.8;
    // 95% Gaussian Confidence Interval: +- 1.96 * sigma
    const upper = val != null ? val + 1.96 * sigma : null;
    const lower = val != null ? val - 1.96 * sigma : null;

    return {
      time: format(parseISO(p.valid_time), 'MMM d HH:mm'),
      'AI MOS Forecast': val,
      'METAR Ground Truth': variable === 'temperature_c' ? act : null,
      'GFS 0.25°': p.gfs?.[variable as keyof typeof p.gfs] ?? null,
      'ECMWF 0.1°': p.ecmwf?.[variable as keyof typeof p.ecmwf] ?? null,
      'JMA GSM': p.jma?.[variable as keyof typeof p.jma] ?? null,
      upper,
      lower,
      uncertaintyBand: upper != null && lower != null ? [lower, upper] : null,
    };
  });

  const h0Label = wuActualTime
    ? format(parseISO(wuActualTime), 'MMM d HH:mm')
    : (data[0]?.time ?? null);

  return (
    <div style={{ width: '100%', height: 320 }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 15, right: 16, left: -10, bottom: 0 }}>
          <defs>
            <linearGradient id="gradMain" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={cfg.color} stopOpacity={0.35} />
              <stop offset="95%" stopColor={cfg.color} stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="gradBand" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#38bdf8" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.6} />
          <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false}
            tickFormatter={v => `${v}${cfg.unit}`} />
          <Tooltip content={<CustomTooltip unit={cfg.unit} />} />
          <Legend iconType="circle" iconSize={8}
            wrapperStyle={{ fontSize: '0.78rem', paddingTop: 10 }} />

          {/* 95% Confidence Interval Shaded Area */}
          <Area
            dataKey="uncertaintyBand"
            stroke="none"
            fill="url(#gradBand)"
            name="95% CI (±1.96σ)"
            connectNulls
          />

          {/* Raw NWP Models */}
          <Area dataKey="GFS 0.25°" type="monotone" stroke="#06b6d4"
            strokeWidth={1.5} strokeDasharray="4 3" fill="none"
            dot={false} connectNulls />
          <Area dataKey="ECMWF 0.1°" type="monotone" stroke="#8b5cf6"
            strokeWidth={1.5} strokeDasharray="4 3" fill="none"
            dot={false} connectNulls />
          <Area dataKey="JMA GSM" type="monotone" stroke="#eab308"
            strokeWidth={1.5} strokeDasharray="4 3" fill="none"
            dot={false} connectNulls />

          {/* Actual METAR Ground Truth Line */}
          {variable === 'temperature_c' && (
            <Area dataKey="METAR Ground Truth" type="monotone" stroke="#10b981"
              strokeWidth={2.5} fill="none"
              dot={{ r: 5, fill: '#10b981', stroke: '#ffffff', strokeWidth: 2 }}
              connectNulls />
          )}

          {/* AI MOS Ensemble Forecast */}
          <Area dataKey="AI MOS Forecast" type="monotone" stroke={cfg.color}
            strokeWidth={2.5} fill="url(#gradMain)"
            dot={false} connectNulls />

          {/* Reference Dot for initial station observation */}
          {variable === 'temperature_c' && wuActualTemp != null && h0Label && (
            <ReferenceDot
              x={h0Label}
              y={wuActualTemp}
              r={7}
              fill="#10b981"
              stroke="#fff"
              strokeWidth={2}
              label={<WUDotLabel value={wuActualTemp} unit={cfg.unit} />}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
