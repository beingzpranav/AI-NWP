import { confidenceColor } from '../utils/format';

interface Props {
  score: number;
  size?: 'sm' | 'md';
}

export default function ConfidenceBadge({ score, size = 'md' }: Props) {
  const color = confidenceColor(score);
  const label = score >= 0.8 ? 'High' : score >= 0.6 ? 'Good' : score >= 0.4 ? 'Fair' : 'Low';
  const pct = Math.round(score * 100);

  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: size === 'sm' ? 4 : 6,
      padding: size === 'sm' ? '2px 8px' : '4px 12px',
      borderRadius: 99,
      background: `${color}18`,
      border: `1px solid ${color}40`,
    }}>
      {/* Mini arc */}
      <svg width={size === 'sm' ? 14 : 18} height={size === 'sm' ? 14 : 18} viewBox="0 0 18 18">
        <circle cx="9" cy="9" r="7" fill="none" stroke="currentColor"
          strokeOpacity={0.2} strokeWidth="2.5" />
        <circle cx="9" cy="9" r="7" fill="none" stroke={color}
          strokeWidth="2.5"
          strokeDasharray={`${score * 44} 44`}
          strokeLinecap="round"
          transform="rotate(-90 9 9)"
          strokeDashoffset="0" />
      </svg>
      <span style={{
        fontSize: size === 'sm' ? '0.7rem' : '0.78rem',
        fontWeight: 700, color,
      }}>
        {pct}% {label}
      </span>
    </div>
  );
}
