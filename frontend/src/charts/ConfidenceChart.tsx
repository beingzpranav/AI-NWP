import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from 'recharts';
import { format, parseISO } from 'date-fns';
import type { ForecastPoint } from '../types/weather';

interface Props { points: ForecastPoint[]; }

export default function ConfidenceChart({ points }: Props) {
  const data = points
    .filter(p => p.uncertainty?.confidence_score != null)
    .map(p => {
      const score = +(p.uncertainty!.confidence_score * 100).toFixed(1);
      const sigma = +(p.uncertainty?.temperature_sigma ?? 0.8).toFixed(2);
      return {
        time: format(parseISO(p.valid_time), 'HH:mm'),
        'Skill Confidence (%)': score,
        'Log-Var Standard Dev σ (°C)': sigma,
      };
    });

  return (
    <div style={{ width: '100%', height: 200 }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 16, left: -16, bottom: 0 }}>
          <defs>
            <linearGradient id="gradConf" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#10b981" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradSigma" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor="#ec4899" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ec4899" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" opacity={0.6} />
          <XAxis dataKey="time" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis yAxisId="left" domain={[0, 100]} tickFormatter={v => `${v}%`}
            tick={{ fontSize: 10, fill: '#10b981' }}
            tickLine={false} axisLine={false} />
          <YAxis yAxisId="right" orientation="right" domain={[0, 3]} tickFormatter={v => `±${v}°C`}
            tick={{ fontSize: 10, fill: '#ec4899' }}
            tickLine={false} axisLine={false} />

          <ReferenceLine yAxisId="left" y={60} stroke="var(--accent-yellow)" strokeDasharray="4 3"
            strokeWidth={1} label={{ value: 'Operational Threshold (60%)', fill: '#eab308', fontSize: 10, position: 'insideTopRight' }} />

          <Tooltip
            contentStyle={{
              background: 'rgba(15, 23, 42, 0.95)', border: '1px solid var(--border)',
              borderRadius: 8, fontSize: '0.78rem', color: '#f8fafc',
            }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.75rem', paddingTop: 6 }} />

          <Area yAxisId="left" dataKey="Skill Confidence (%)" type="monotone" stroke="#10b981" strokeWidth={2}
            fill="url(#gradConf)" dot={false} connectNulls />

          <Area yAxisId="right" dataKey="Log-Var Standard Dev σ (°C)" type="monotone" stroke="#ec4899" strokeWidth={2}
            strokeDasharray="4 3" fill="url(#gradSigma)" dot={false} connectNulls />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
