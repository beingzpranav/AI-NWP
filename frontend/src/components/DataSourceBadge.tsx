interface Props {
  source: string;
  available: boolean;
  showLabel?: boolean;
}

const SOURCE_META: Record<string, { color: string; icon: string }> = {
  GFS:           { color: '#06b6d4', icon: '🌐' },
  ECMWF:         { color: '#3b82f6', icon: '🌐' },
  JMA:           { color: '#8b5cf6', icon: '🌐' },
  weather_union: { color: '#22c55e', icon: '📡' },
  ML:            { color: '#ec4899', icon: '🧠' },
};

export default function DataSourceBadge({ source, available, showLabel = true }: Props) {
  const meta = SOURCE_META[source] ?? { color: '#6b7280', icon: '•' };
  const label = source === 'weather_union' ? 'Weather Union' : source.toUpperCase();

  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '3px 10px', borderRadius: 99,
      background: available ? `${meta.color}15` : 'rgba(107,114,128,0.1)',
      border: `1px solid ${available ? `${meta.color}40` : 'rgba(107,114,128,0.2)'}`,
      fontSize: '0.72rem', fontWeight: 600,
      color: available ? meta.color : 'var(--text-muted)',
    }}>
      <span>{meta.icon}</span>
      {showLabel && <span>{label}</span>}
      <div style={{
        width: 5, height: 5, borderRadius: '50%',
        background: available ? meta.color : '#6b7280',
        boxShadow: available ? `0 0 4px ${meta.color}` : 'none',
      }} />
    </div>
  );
}
