import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';

interface Props { points: ForecastPoint[]; }

export default function WUCorrectionChart({ points }: Props) {
  const data = points.slice(0, 24).map(p => {
    const nwpVals = [
      p.gfs?.temperature_c,
      p.ecmwf?.temperature_c,
      p.jma?.temperature_c,
    ].filter((v): v is number => v != null);
    const nwpMean = nwpVals.length
      ? nwpVals.reduce((a, b) => a + b, 0) / nwpVals.length
      : null;
    const aiTemp  = p.temperature_c ?? null;
    const correction = aiTemp != null && nwpMean != null
      ? +(aiTemp - nwpMean).toFixed(2) : null;

    return {
      time:       format(parseISO(p.valid_time), 'HH:mm'),
      'NWP Mean': nwpMean  != null ? +nwpMean.toFixed(1)  : null,
      'AI Corrected': aiTemp != null ? +aiTemp.toFixed(1) : null,
      'WU Correction': correction,
    };
  });

  return (
    <div style={{ width: '100%', height: 240 }}>
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
          <YAxis yAxisId="corr" orientation="right"
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false}
            tickFormatter={v => `${v > 0 ? '+' : ''}${v}°`} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 8, fontSize: '0.78rem',
            }}
            formatter={(v: number, name: string) => [
              `${v > 0 && name === 'WU Correction' ? '+' : ''}${v?.toFixed(1)}°C`, name,
            ]}
          />
          <Legend iconType="circle" iconSize={8}
            wrapperStyle={{ fontSize: '0.78rem' }} />
          <ReferenceLine yAxisId="corr" y={0}
            stroke="var(--text-muted)" strokeDasharray="3 3" />

          <Line yAxisId="temp" type="monotone" dataKey="NWP Mean"
            stroke="#6b7280" strokeWidth={1.5} strokeDasharray="5 3"
            dot={false} connectNulls />
          <Line yAxisId="temp" type="monotone" dataKey="AI Corrected"
            stroke="#06b6d4" strokeWidth={2.5}
            dot={false} connectNulls />
          <Bar yAxisId="corr" dataKey="WU Correction"
            fill="rgba(6,182,212,0.3)" stroke="rgba(6,182,212,0.7)"
            strokeWidth={1} radius={[2, 2, 0, 0]} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
