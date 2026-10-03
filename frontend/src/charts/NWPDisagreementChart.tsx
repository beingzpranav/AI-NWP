import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';

interface Props { points: ForecastPoint[]; }

export default function NWPDisagreementChart({ points }: Props) {
  const data = points.slice(0, 48).map(p => {
    const vals = [
      p.gfs?.temperature_c,
      p.ecmwf?.temperature_c,
      p.jma?.temperature_c,
    ].filter((v): v is number => v != null);

    const spread = vals.length > 1 ? Math.max(...vals) - Math.min(...vals) : null;
    const mean   = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;

    return {
      time:    format(parseISO(p.valid_time), 'HH:mm'),
      GFS:     p.gfs?.temperature_c  ?? null,
      ECMWF:   p.ecmwf?.temperature_c ?? null,
      JMA:     p.jma?.temperature_c  ?? null,
      AI:      p.temperature_c       ?? null,
      Spread:  spread != null ? +spread.toFixed(2) : null,
    };
  });

  return (
    <div style={{ width: '100%', height: 280 }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 5, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="time"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false}
            interval="preserveStartEnd" />
          <YAxis yAxisId="temp"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false}
            tickFormatter={v => `${v}°`} />
          <YAxis yAxisId="spread" orientation="right"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false}
            tickFormatter={v => `${v}°`} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 8, fontSize: '0.78rem',
            }}
            formatter={(v: number, name: string) => [`${v?.toFixed(1)}°C`, name]}
          />
          <Legend iconType="circle" iconSize={8}
            wrapperStyle={{ fontSize: '0.78rem' }} />

          {/* NWP model lines */}
          <Line yAxisId="temp" type="monotone" dataKey="GFS"
            stroke="#06b6d4" strokeWidth={1.5} strokeDasharray="4 3"
            dot={false} connectNulls />
          <Line yAxisId="temp" type="monotone" dataKey="ECMWF"
            stroke="#3b82f6" strokeWidth={1.5} strokeDasharray="4 3"
            dot={false} connectNulls />
          <Line yAxisId="temp" type="monotone" dataKey="JMA"
            stroke="#8b5cf6" strokeWidth={1.5} strokeDasharray="4 3"
            dot={false} connectNulls />
          {/* AI ensemble */}
          <Line yAxisId="temp" type="monotone" dataKey="AI"
            stroke="#f97316" strokeWidth={2.5}
            dot={false} connectNulls />
          {/* Spread bars on right axis */}
          <Bar yAxisId="spread" dataKey="Spread"
            fill="rgba(234,179,8,0.25)" stroke="rgba(234,179,8,0.6)"
            strokeWidth={1} radius={[2, 2, 0, 0]} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
