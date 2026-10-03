import { useState, useRef } from 'react';
import { Search, MapPin, Loader } from 'lucide-react';
import { searchLocations, createLocation } from '../services/api';
import type { Location } from '../types/weather';

interface Props {
  onSelect: (lat: number, lon: number, label: string) => void;
}

// All 14 Indian cities with 1-year historical dataset & trained models
const QUICK_LOCATIONS = [
  { label: 'New Delhi',    lat: 28.6139, lon: 77.2090 },
  { label: 'Jaipur',       lat: 26.9124, lon: 75.7873 },
  { label: 'Bengaluru',    lat: 12.9716, lon: 77.5946 },
  { label: 'Hyderabad',    lat: 17.3850, lon: 78.4867 },
  { label: 'Mumbai',       lat: 19.0760, lon: 72.8777 },
  { label: 'Chennai',      lat: 13.0827, lon: 80.2707 },
  { label: 'Kolkata',      lat: 22.5726, lon: 88.3639 },
  { label: 'Pune',         lat: 18.5204, lon: 73.8567 },
  { label: 'Ahmedabad',    lat: 23.0225, lon: 72.5714 },
  { label: 'Lucknow',      lat: 26.8467, lon: 80.9462 },
  { label: 'Chandigarh',   lat: 30.7333, lon: 76.7794 },
  { label: 'Bhopal',       lat: 23.2599, lon: 77.4126 },
  { label: 'Patna',        lat: 25.5941, lon: 85.1376 },
  { label: 'Kochi',        lat: 9.9312,  lon: 76.2673 },
];

export default function LocationSearch({ onSelect }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Location[]>([]);
  const [searching, setSearching] = useState(false);
  const [open, setOpen] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const handleInput = (val: string) => {
    setQuery(val);
    clearTimeout(debounceRef.current);
    if (val.length < 2) { setResults([]); return; }
    setSearching(true);
    debounceRef.current = setTimeout(async () => {
      try {
        const locs = await searchLocations(val);
        setResults(locs);
      } catch { setResults([]); }
      finally { setSearching(false); }
    }, 400);
  };

  const filteredQuick = query
    ? QUICK_LOCATIONS.filter(loc => loc.label.toLowerCase().includes(query.toLowerCase()))
    : QUICK_LOCATIONS;

  return (
    <div style={{ position: 'relative' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--bg-elevated)', border: '1px solid var(--border)',
        borderRadius: 10, padding: '8px 14px',
        transition: 'border-color var(--transition)',
      }}
        onFocus={() => setOpen(true)}
      >
        <Search size={15} color="var(--text-muted)" />
        <input
          value={query}
          onChange={e => handleInput(e.target.value)}
          onFocus={() => setOpen(true)}
          placeholder="Search 14 trained cities or custom location…"
          style={{
            background: 'none', border: 'none', outline: 'none',
            color: 'var(--text-primary)', fontSize: '0.875rem', flex: 1,
          }}
        />
        {searching && <Loader size={14} className="animate-spin" color="var(--accent-blue)" />}
        <button
          type="button"
          onClick={() => setOpen(prev => !prev)}
          style={{
            background: 'none', border: 'none', color: 'var(--text-muted)',
            cursor: 'pointer', fontSize: '0.75rem', padding: '2px 4px',
          }}
        >
          ▾
        </button>
      </div>

      {open && (
        <div style={{
          position: 'absolute', top: '110%', left: 0, right: 0, zIndex: 200,
          background: 'var(--bg-card)', border: '1px solid var(--border)',
          borderRadius: 12, boxShadow: 'var(--shadow-elevated)',
          maxHeight: 360, overflowY: 'auto',
        }}>
          {/* Header */}
          <div style={{
            padding: '8px 14px 4px',
            fontSize: '0.7rem', color: 'var(--accent-blue)', fontWeight: 600,
            letterSpacing: '0.05em', textTransform: 'uppercase',
            display: 'flex', justifyContent: 'space-between',
          }}>
            <span>14 Trained Dataset Cities</span>
            <span style={{ color: 'var(--text-muted)' }}>{filteredQuick.length} cities</span>
          </div>

          {/* Quick 14 cities list */}
          {filteredQuick.map(loc => (
            <button key={loc.label} onClick={() => { onSelect(loc.lat, loc.lon, loc.label); setOpen(false); setQuery(loc.label); }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 14px', background: 'none', border: 'none',
                cursor: 'pointer', color: 'var(--text-primary)', fontSize: '0.875rem',
                textAlign: 'left', transition: 'background var(--transition)',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'none')}
            >
              <MapPin size={13} color="var(--accent-blue)" />
              <span style={{ fontWeight: 500 }}>{loc.label}</span>
              <span style={{
                fontSize: '0.65rem', background: 'rgba(59, 130, 246, 0.15)',
                color: 'var(--accent-blue)', padding: '2px 6px', borderRadius: 4, marginLeft: 6,
              }}>
                ML Trained
              </span>
              <span style={{ marginLeft: 'auto', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {loc.lat.toFixed(2)}, {loc.lon.toFixed(2)}
              </span>
            </button>
          ))}

          {/* Additional database search results if any */}
          {results.filter(r => !QUICK_LOCATIONS.some(q => q.label.toLowerCase() === r.name.toLowerCase())).map(loc => (
            <button key={loc.id}
              onClick={() => { onSelect(loc.latitude, loc.longitude, loc.name); setOpen(false); setQuery(loc.name); }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                padding: '9px 14px', background: 'none', border: 'none',
                cursor: 'pointer', color: 'var(--text-primary)', fontSize: '0.875rem',
                textAlign: 'left',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-elevated)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'none')}
            >
              <MapPin size={13} color="var(--accent-cyan)" />
              {loc.name} {loc.city && `· ${loc.city}`}
            </button>
          ))}

          {query.length >= 2 && !searching && filteredQuick.length === 0 && results.length === 0 && (
            <div style={{ padding: '12px 14px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              No matching cities found. Try one of the 14 trained cities (e.g. Pune, Jaipur, Bengaluru, Mumbai).
            </div>
          )}
        </div>
      )}
    </div>
  );
}
