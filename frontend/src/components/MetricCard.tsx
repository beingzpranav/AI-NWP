import { ReactNode } from 'react';
import clsx from 'clsx';

interface Props {
  label: string;
  value: string | ReactNode;
  subValue?: string;
  icon?: ReactNode;
  trend?: 'up' | 'down' | 'neutral';
  color?: string;
  loading?: boolean;
}

export default function MetricCard({ label, value, subValue, icon, color, loading }: Props) {
  if (loading) {
    return (
      <div className="card" style={{ padding: 20 }}>
        <div className="skeleton" style={{ height: 14, width: '60%', marginBottom: 12 }} />
        <div className="skeleton" style={{ height: 32, width: '80%', marginBottom: 8 }} />
        <div className="skeleton" style={{ height: 12, width: '40%' }} />
      </div>
    );
  }

  return (
    <div className="card animate-fade-in" style={{
      padding: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Subtle color accent on top */}
      {color && (
        <div style={{
          position: 'absolute', top: 0, left: 0, right: 0, height: 2,
          background: color,
        }} />
      )}

      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'
      }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)',
                       fontWeight: 500, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
          {label}
        </span>
        {icon && (
          <span style={{ color: color || 'var(--text-muted)', opacity: 0.7 }}>
            {icon}
          </span>
        )}
      </div>

      <div style={{ fontSize: '1.75rem', fontWeight: 700, lineHeight: 1.1,
                    color: color || 'var(--text-primary)', fontVariantNumeric: 'tabular-nums' }}>
        {value}
      </div>

      {subValue && (
        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {subValue}
        </div>
      )}
    </div>
  );
}
