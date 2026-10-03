import { Link, useLocation } from 'react-router-dom';
import { Sun, Moon, Activity, CloudRain, BarChart3, Map, Database } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';
import { useHealth } from '../hooks/useWeather';

const NAV_ITEMS = [
  { to: '/',          label: 'Dashboard',  Icon: CloudRain },
  { to: '/forecast',  label: 'Forecast',   Icon: Activity },
  { to: '/models',    label: 'AI Models',  Icon: BarChart3 },
  { to: '/map',       label: 'Map',        Icon: Map },
  { to: '/pipeline',  label: 'Pipeline',   Icon: Database },
];

export default function Navbar() {
  const { theme, toggle } = useTheme();
  const location = useLocation();
  const { data: health } = useHealth();

  return (
    <nav style={{
      position: 'fixed', top: 0, left: 0, right: 0, zIndex: 100,
      background: 'var(--bg-glass)',
      backdropFilter: 'blur(20px)',
      WebkitBackdropFilter: 'blur(20px)',
      borderBottom: '1px solid var(--border)',
      height: 60,
      display: 'flex', alignItems: 'center',
      padding: '0 24px',
      gap: 8,
    }}>
      {/* Logo */}
      <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: 10, marginRight: 24 }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16,
        }}>🌤</div>
        <span style={{ fontWeight: 700, fontSize: '1rem', letterSpacing: '-0.02em' }}
              className="text-gradient">
          WeatherAI
        </span>
      </Link>

      {/* Nav items */}
      <div style={{ display: 'flex', gap: 4, flex: 1 }}>
        {NAV_ITEMS.map(({ to, label, Icon }) => {
          const active = location.pathname === to;
          return (
            <Link key={to} to={to} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 14px', borderRadius: 'var(--radius-sm)',
              fontSize: '0.875rem', fontWeight: active ? 600 : 400,
              color: active ? 'var(--text-accent)' : 'var(--text-secondary)',
              background: active ? 'rgba(59,130,246,0.12)' : 'transparent',
              transition: 'all var(--transition)',
              textDecoration: 'none',
            }}>
              <Icon size={15} />
              <span className="nav-label">{label}</span>
            </Link>
          );
        })}
      </div>

      {/* Right side */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        {/* Backend status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{
            width: 7, height: 7, borderRadius: '50%',
            background: health?.status === 'ok' ? 'var(--accent-green)' : 'var(--accent-red)',
            boxShadow: health?.status === 'ok' ? '0 0 6px var(--accent-green)' : 'none',
          }} />
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
            {health?.status === 'ok' ? 'Online' : 'Offline'}
          </span>
        </div>

        {/* WU badge */}
        {health && (
          <span className={`badge ${health.weather_union_configured ? 'badge-cyan' : 'badge-yellow'}`}>
            WU {health.weather_union_configured ? 'Active' : 'Setup Required'}
          </span>
        )}

        {/* Theme toggle */}
        <button onClick={toggle} style={{
          background: 'var(--bg-elevated)', border: '1px solid var(--border)',
          borderRadius: 8, padding: 7, cursor: 'pointer',
          color: 'var(--text-secondary)', display: 'flex',
          transition: 'all var(--transition)',
        }}>
          {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
        </button>
      </div>
    </nav>
  );
}
