import { AlertTriangle } from 'lucide-react';

interface Props {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

export default function ErrorState({
  title = 'Something went wrong',
  message,
  onRetry,
}: Props) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      padding: 48, gap: 12, textAlign: 'center',
    }}>
      <div style={{
        width: 48, height: 48, borderRadius: 12,
        background: 'rgba(239,68,68,0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <AlertTriangle size={24} color="var(--accent-red)" />
      </div>
      <div style={{ fontWeight: 600 }}>{title}</div>
      {message && (
        <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', maxWidth: 360 }}>
          {message}
        </div>
      )}
      {onRetry && (
        <button onClick={onRetry} style={{
          marginTop: 8, padding: '8px 20px',
          background: 'var(--accent-blue)', color: '#fff',
          border: 'none', borderRadius: 8, cursor: 'pointer',
          fontSize: '0.875rem', fontWeight: 500,
        }}>
          Retry
        </button>
      )}
    </div>
  );
}
