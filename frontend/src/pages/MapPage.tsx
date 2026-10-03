import { useState } from 'react';
import { MapPin, Compass, ShieldCheck, Award, Layers } from 'lucide-react';
import WeatherMap, { SYNOPTIC_STATIONS, SynopticStation } from '../maps/WeatherMap';
import LocationSearch from '../components/LocationSearch';
import WeatherUnionStatus from '../components/WeatherUnionStatus';
import MetricCard from '../components/MetricCard';
import { useCurrentConditions, useForecast } from '../hooks/useWeather';
import { useLocationState } from '../hooks/useLocation';
import { fmt, windDirection } from '../utils/format';
import { Thermometer, Droplets, Wind, CloudRain } from 'lucide-react';

export default function MapPage() {
  const { coords, setLocation } = useLocationState();
  const { data: current, isLoading } = useCurrentConditions(coords.lat, coords.lon);
  const { data: forecast } = useForecast(coords.lat, coords.lon, 6);
  const currentPoint = forecast?.points?.[0];

  const matchedStation = SYNOPTIC_STATIONS.find(
    s => Math.abs(s.lat - coords.lat) < 0.3 && Math.abs(s.lon - coords.lon) < 0.3
  );

  return (
    <div style={{ padding: 24, maxWidth: 1400, margin: '0 auto' }}>
      <div style={{ marginBottom: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 4 }}>
            <MapPin size={20} style={{ marginRight: 8, verticalAlign: 'middle', color: 'var(--accent-blue)' }} />
            Synoptic Meteorological Weather Map
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Interactive 14-City METAR Station Network · Multi-Model Basemaps · Real-time Surface Observations
          </p>
        </div>

        {matchedStation && (
          <div style={{ padding: '8px 14px', borderRadius: 10, background: 'rgba(14, 165, 233, 0.1)', border: '1px solid rgba(14, 165, 233, 0.3)', display: 'flex', alignItems: 'center', gap: 10 }}>
            <Award size={18} style={{ color: 'var(--accent-cyan)' }} />
            <div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Active Airport Station</div>
              <div style={{ fontWeight: 700, fontSize: '0.88rem', color: 'var(--text-primary)' }}>
                {matchedStation.city} (<span style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-blue)' }}>{matchedStation.icao}</span>)
                {matchedStation.skill > 0 && <span className="badge badge-green" style={{ marginLeft: 8 }}>+{matchedStation.skill}% Skill</span>}
              </div>
            </div>
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>

        {/* Map + search */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <LocationSearch onSelect={(lat, lon, label) => setLocation(lat, lon, label)} />

          <div style={{ height: 520 }}>
            <WeatherMap
              lat={coords.lat}
              lon={coords.lon}
              label={coords.label}
              currentTemp={current?.temperature_c ?? currentPoint?.temperature_c}
              onMapClick={(lat, lon) => setLocation(lat, lon, `${lat.toFixed(2)}°N, ${lon.toFixed(2)}°E`)}
              onSelectStation={(st) => setLocation(st.lat, st.lon, `${st.city} (${st.icao})`)}
            />
          </div>

          {/* Featured 14 Synoptic Stations selector */}
          <div className="card" style={{ padding: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                14-City Synoptic METAR Stations
              </div>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Click to center map</span>
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {SYNOPTIC_STATIONS.map(st => {
                const isActive = coords.label.includes(st.city) || (Math.abs(st.lat - coords.lat) < 0.2 && Math.abs(st.lon - coords.lon) < 0.2);
                return (
                  <button
                    key={st.icao}
                    onClick={() => setLocation(st.lat, st.lon, `${st.city} (${st.icao})`)}
                    style={{
                      padding: '5px 12px', borderRadius: 99,
                      border: '1px solid var(--border)',
                      background: isActive ? 'var(--accent-blue)' : 'var(--bg-elevated)',
                      color: isActive ? '#fff' : 'var(--text-secondary)',
                      fontSize: '0.78rem', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: 6,
                      transition: 'all var(--transition)',
                    }}
                  >
                    <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{st.icao}</span>
                    <span>{st.city}</span>
                    {st.skill > 0 && (
                      <span style={{ fontSize: '0.68rem', padding: '1px 5px', borderRadius: 4, background: isActive ? 'rgba(255,255,255,0.25)' : 'rgba(34, 197, 94, 0.15)', color: isActive ? '#fff' : '#22c55e', fontWeight: 700 }}>
                        +{st.skill}%
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Sidebar panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Location info */}
          <div className="card" style={{ padding: 18 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
              <MapPin size={18} color="var(--accent-blue)" />
              <div>
                <div style={{ fontWeight: 700, fontSize: '1rem' }}>{coords.label}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {coords.lat.toFixed(4)}°N, {coords.lon.toFixed(4)}°E
                </div>
              </div>
            </div>
            {matchedStation && (
              <div style={{ marginTop: 10, paddingTop: 10, borderTop: '1px solid var(--border)', fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
                <div>1-Year Factual Training: <strong>8,784 Hourly Samples</strong></div>
                <div>Raw NWP MAE Baseline: <strong style={{ color: '#38bdf8' }}>{matchedStation.mae.toFixed(2)}°C</strong></div>
              </div>
            )}
          </div>

          {/* Current conditions */}
          <MetricCard
            label="Temperature" loading={isLoading}
            value={fmt.temp(current?.temperature_c ?? currentPoint?.temperature_c)}
            subValue={current?.weather_union_available ? `WU Obs: ${fmt.temp(current.weather_union_temp)}` : 'NWP Ensemble MOS'}
            icon={<Thermometer size={16} />}
            color="#f97316"
          />
          <MetricCard
            label="Humidity" loading={isLoading}
            value={fmt.pct(current?.humidity_pct ?? currentPoint?.humidity_pct)}
            icon={<Droplets size={16} />} color="var(--accent-cyan)"
          />
          <MetricCard
            label="Wind Vector" loading={isLoading}
            value={fmt.wind(current?.wind_speed_kmh ?? currentPoint?.wind_speed_kmh)}
            subValue={windDirection(current?.wind_direction_deg)}
            icon={<Wind size={16} />} color="var(--accent-purple)"
          />
          <MetricCard
            label="Rainfall Rate" loading={isLoading}
            value={fmt.mm(current?.precipitation_mm ?? currentPoint?.precipitation_mm)}
            icon={<CloudRain size={16} />} color="var(--accent-blue)"
          />

          <WeatherUnionStatus lat={coords.lat} lon={coords.lon} />
        </div>
      </div>
    </div>
  );
}
