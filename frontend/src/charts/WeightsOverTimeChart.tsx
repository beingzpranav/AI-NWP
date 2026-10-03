import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer,
} from 'recharts';

// Generates illustrative weight-over-time data
// In production this is fetched from the DB after each training cycle
function generateWeightHistory() {
  const data = [];
  const base = { ECMWF: 0.40, GFS: 0.30, JMA: 0.20, ML: 0.10 };
  for (let i = 23; i >= 0; i--) {
    const noise = () => (Math.random() - 0.5) * 0.06;
    const raw = {
      ECMWF: Math.max(0.1, base.ECMWF + noise()),
      GFS:   Math.max(0.1, base.GFS   + noise()),
      JMA:   Math.max(0.05, base.JMA  + noise()),
      ML:    Math.max(0.05, base.ML   + noise()),
    };
    const sum = raw.ECMWF + raw.GFS + raw.JMA + raw.ML;
    data.push({
      hour: `-${i}h`,
      ECMWF: +(raw.ECMWF / sum).toFixed(3),
      GFS:   +(raw.GFS   / sum).toFixed(3),
      JMA:   +(raw.JMA   / sum).toFixed(3),
      ML:    +(raw.ML    / sum).toFixed(3),
    });
  }
  return data;
}

const COLORS = { ECMWF: '#3b82f6', GFS: '#06b6d4', JMA: '#8b5cf6', ML: '#22c55e' };

export default function WeightsOverTimeChart() {
  const data = generateWeightHistory();

  return (
    <div style={{ width: '100%', height: 220 }}>
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 5, right: 16, left: -10, bottom: 0 }}
          stackOffset="expand">
          <defs>
            {Object.entries(COLORS).map(([k, c]) => (
              <linearGradient key={k} id={`grad${k}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={c} stopOpacity={0.8} />
                <stop offset="95%" stopColor={c} stopOpacity={0.3} />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="hour" tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false} interval={3} />
          <YAxis tickFormatter={v => `${(v * 100).toFixed(0)}%`}
            tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false} />
          <Tooltip
            formatter={(v: number) => `${(v * 100).toFixed(1)}%`}
            contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border)',
                            borderRadius: 8, fontSize: '0.78rem' }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.78rem' }} />
          {Object.entries(COLORS).map(([k, c]) => (
            <Area key={k} type="monotone" dataKey={k} stackId="1"
              stroke={c} fill={`url(#grad${k})`} strokeWidth={1.5} />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
