import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';
import { useModelComparison } from '../hooks/useWeather';

const COLORS: Record<string, string> = {
  GFS: '#06b6d4', ECMWF: '#3b82f6', JMA: '#8b5cf6',
  RF: '#22c55e', XGBoost: '#f97316', AdaBoost: '#eab308',
  ANN: '#ec4899', ANN_two_head: '#ec4899',
};

export default function ModelErrorChart() {
  const { data, isLoading } = useModelComparison();

  if (isLoading) {
    return <div className="skeleton" style={{ height: 200, borderRadius: 8 }} />;
  }

  const models = data?.models || [];
  if (!models.length) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.875rem' }}>
        No performance data yet. Train models first.
      </div>
    );
  }

  const chartData = models
    .filter(m => m.avg_mae != null)
    .map(m => ({ name: m.model, MAE: m.avg_mae, RMSE: m.avg_rmse, R2: m.avg_r2 }));

  return (
    <div style={{ width: '100%', height: 240 }}>
      <ResponsiveContainer>
        <BarChart data={chartData} margin={{ top: 5, right: 16, left: -10, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }}
            tickLine={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 8, fontSize: '0.8rem',
            }}
          />
          <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: '0.78rem' }} />
          <Bar dataKey="MAE" name="MAE" radius={[4, 4, 0, 0]}>
            {chartData.map(entry => (
              <Cell key={entry.name} fill={COLORS[entry.name] || '#6b7280'} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
