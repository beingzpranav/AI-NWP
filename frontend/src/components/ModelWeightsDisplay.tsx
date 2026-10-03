import { useModelWeights } from '../hooks/useWeather';
import type { ModelWeights } from '../types/weather';

const MODEL_COLORS: Record<string, string> = {
  ECMWF: '#3b82f6',
  GFS:   '#06b6d4',
  JMA:   '#8b5cf6',
  ML:    '#22c55e',
};

interface Props {
  /** If provided, these city-specific weights override the global API weights */
  overrideWeights?: ModelWeights | null;
}

export default function ModelWeightsDisplay({ overrideWeights }: Props = {}) {
  const { data: weightsData, isLoading } = useModelWeights();

  if (isLoading && !overrideWeights) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 100, borderRadius: 8 }} />
      </div>
    );
  }

  // Prefer city-specific weights from forecast points, fall back to global API
  let weights: Record<string, number> | undefined;
  if (overrideWeights) {
    weights = {
      ECMWF: overrideWeights.ecmwf,
      GFS:   overrideWeights.gfs,
      JMA:   overrideWeights.jma,
      ML:    overrideWeights.ml,
    };
  } else {
    weights = weightsData?.weights as Record<string, number> | undefined;
  }

  if (!weights) return null;

  const isLive = !!overrideWeights;

  return (
    <div className="card" style={{ padding: 20 }}>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>Dynamic Model Weights</span>
        <span className="badge badge-blue">{isLive ? 'LIVE' : 'GLOBAL'}</span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {Object.entries(weights)
          .sort(([, a], [, b]) => b - a)
          .map(([model, weight]) => {
            const pct = (weight * 100).toFixed(1);
            const color = MODEL_COLORS[model] || '#6b7280';
            return (
              <div key={model}>
                <div style={{
                  display: 'flex', justifyContent: 'space-between',
                  marginBottom: 5, fontSize: '0.8rem',
                }}>
                  <span style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>{model}</span>
                  <span style={{ fontWeight: 700, color }}>{pct}%</span>
                </div>
                <div style={{
                  height: 6, background: 'var(--bg-elevated)',
                  borderRadius: 3, overflow: 'hidden',
                }}>
                  <div style={{
                    height: '100%', width: `${pct}%`,
                    background: color,
                    borderRadius: 3,
                    transition: 'width 0.6s cubic-bezier(0.4,0,0.2,1)',
                    boxShadow: `0 0 8px ${color}60`,
                  }} />
                </div>
              </div>
            );
          })}
      </div>

      <div style={{ marginTop: 12, fontSize: '0.73rem', color: 'var(--text-muted)' }}>
        {isLive
          ? 'City-specific weights from trained model MAE scores'
          : 'Weights computed from recent forecast errors · updates every 2 min'}
      </div>
    </div>
  );
}
