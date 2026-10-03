import { format, parseISO } from 'date-fns';

export const fmt = {
  temp: (v?: number) => v != null ? `${v.toFixed(1)}°C` : '—',
  pct:  (v?: number) => v != null ? `${v.toFixed(0)}%` : '—',
  wind: (v?: number) => v != null ? `${v.toFixed(1)} km/h` : '—',
  hpa:  (v?: number) => v != null ? `${v.toFixed(0)} hPa` : '—',
  mm:   (v?: number) => v != null ? `${v.toFixed(1)} mm` : '—',
  pct2: (v?: number) => v != null ? `${(v * 100).toFixed(0)}%` : '—',
  time: (iso: string) => format(parseISO(iso), 'HH:mm'),
  date: (iso: string) => format(parseISO(iso), 'MMM d'),
  datetime: (iso: string) => format(parseISO(iso), 'MMM d, HH:mm'),
};

export const windDirection = (deg?: number): string => {
  if (deg == null) return '—';
  const dirs = ['N','NE','E','SE','S','SW','W','NW'];
  return dirs[Math.round(deg / 45) % 8];
};

export const confidenceColor = (score: number): string => {
  if (score >= 0.8) return '#22c55e';
  if (score >= 0.6) return '#eab308';
  if (score >= 0.4) return '#f97316';
  return '#ef4444';
};

export const weatherIcon = (temp?: number, precip?: number): string => {
  if (precip != null && precip > 1) return '🌧️';
  if (temp != null && temp > 35) return '🌡️';
  if (temp != null && temp < 10) return '🥶';
  return '⛅';
};
