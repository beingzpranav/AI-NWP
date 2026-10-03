import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMap, useMapEvents } from 'react-leaflet';
import { icon, divIcon } from 'leaflet';
import 'leaflet/dist/leaflet.css';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { fmt } from '../utils/format';

const defaultIcon = icon({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34],
});

export interface SynopticStation {
  city: string;
  icao: string;
  lat: number;
  lon: number;
  skill: number;
  mae: number;
}

export const SYNOPTIC_STATIONS: SynopticStation[] = [
  { city: 'Delhi',      icao: 'VIDP', lat: 28.56, lon: 77.10, skill: 0.0,  mae: 1.19 },
  { city: 'Mumbai',     icao: 'VABB', lat: 19.08, lon: 72.88, skill: 28.7, mae: 0.67 },
  { city: 'Bengaluru',  icao: 'VOBL', lat: 12.98, lon: 77.59, skill: 12.8, mae: 0.82 },
  { city: 'Hyderabad',  icao: 'VOHS', lat: 17.39, lon: 78.49, skill: 22.8, mae: 0.95 },
  { city: 'Chennai',    icao: 'VOMM', lat: 13.08, lon: 80.27, skill: 9.7,  mae: 0.93 },
  { city: 'Kolkata',    icao: 'VECC', lat: 22.65, lon: 88.45, skill: 0.0,  mae: 0.83 },
  { city: 'Ahmedabad',  icao: 'VAAH', lat: 23.07, lon: 72.63, skill: 45.3, mae: 0.88 },
  { city: 'Kochi',      icao: 'VOCI', lat: 9.93,  lon: 76.26, skill: 34.6, mae: 0.72 },
  { city: 'Pune',       icao: 'VAPO', lat: 18.58, lon: 73.92, skill: 0.0,  mae: 0.44 },
  { city: 'Jaipur',     icao: 'VIJP', lat: 26.82, lon: 75.80, skill: 0.0,  mae: 0.83 },
  { city: 'Lucknow',    icao: 'VILK', lat: 26.76, lon: 80.88, skill: 0.0,  mae: 1.05 },
  { city: 'Chandigarh', icao: 'VICG', lat: 30.67, lon: 76.79, skill: 0.0,  mae: 0.98 },
  { city: 'Bhopal',     icao: 'VABP', lat: 23.26, lon: 77.41, skill: 0.0,  mae: 1.12 },
  { city: 'Patna',      icao: 'VEPT', lat: 25.59, lon: 85.09, skill: 0.0,  mae: 1.08 },
];

const TILE_SOURCES = [
  {
    name: 'OpenStreetMap',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenStreetMap contributors',
  },
  {
    name: 'Esri Satellite',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    attribution: 'Tiles &copy; Esri',
  },
  {
    name: 'OpenTopoMap',
    url: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '&copy; OpenTopoMap',
  },
];

function RecenterMap({ lat, lon }: { lat: number; lon: number }) {
  const map = useMap();
  useEffect(() => { map.setView([lat, lon], 7); }, [lat, lon, map]);
  return null;
}

function ResizeFix() {
  const map = useMap();
  useEffect(() => {
    const container = map.getContainer();
    const observer = new ResizeObserver(() => map.invalidateSize());
    observer.observe(container);
    const timer = setTimeout(() => map.invalidateSize(), 200);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, [map]);
  return null;
}

function ClickHandler({ onMapClick }: { onMapClick?: (lat: number, lon: number) => void }) {
  useMapEvents({ click: e => onMapClick?.(e.latlng.lat, e.latlng.lng) });
  return null;
}

function createStationIcon(station: SynopticStation, isSelected: boolean) {
  const isHighSkill = station.skill > 20;
  const bg = isSelected ? '#3b82f6' : isHighSkill ? '#10b981' : '#64748b';
  
  return divIcon({
    className: 'custom-station-pin',
    html: `
      <div style="
        background: ${bg};
        color: white;
        padding: 3px 7px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 10px;
        font-family: monospace;
        box-shadow: 0 2px 6px rgba(0,0,0,0.4);
        border: 2px solid ${isSelected ? '#ffffff' : 'rgba(255,255,255,0.7)'};
        white-space: nowrap;
        display: flex;
        align-items: center;
        gap: 4px;
        transform: translate(-50%, -50%);
      ">
        <span>${station.icao}</span>
        ${station.skill > 0 ? `<span style="background: rgba(255,255,255,0.25); padding: 0 4px; border-radius: 6px;">+${station.skill}%</span>` : ''}
      </div>
    `,
    iconSize: [60, 24],
    iconAnchor: [30, 12],
  });
}

interface Props {
  lat: number;
  lon: number;
  label: string;
  currentTemp?: number;
  onMapClick?: (lat: number, lon: number) => void;
  onSelectStation?: (station: SynopticStation) => void;
}

export default function WeatherMap({ lat, lon, label, currentTemp, onMapClick, onSelectStation }: Props) {
  const [tileIdx, setTileIdx] = useState(0);
  const tiles = TILE_SOURCES[tileIdx];

  return (
    <div style={{
      height: '100%', minHeight: 450,
      borderRadius: 'var(--radius-lg)', overflow: 'hidden',
      border: '1px solid var(--border)',
      position: 'relative',
    }}>
      {/* Map Tile Layer Selector Controls */}
      <div style={{
        position: 'absolute', top: 12, right: 12, zIndex: 1000,
        background: 'rgba(15, 23, 42, 0.85)', backdropFilter: 'blur(8px)',
        border: '1px solid var(--border)', padding: 4, borderRadius: 8,
        display: 'flex', gap: 4,
      }}>
        {TILE_SOURCES.map((t, i) => (
          <button
            key={t.name}
            onClick={() => setTileIdx(i)}
            style={{
              padding: '4px 10px', borderRadius: 6, border: 'none', cursor: 'pointer',
              fontSize: '0.72rem', fontWeight: 600,
              background: tileIdx === i ? 'var(--accent-blue)' : 'transparent',
              color: tileIdx === i ? '#fff' : '#94a3b8',
            }}
          >
            {t.name}
          </button>
        ))}
      </div>

      <MapContainer
        center={[lat, lon]}
        zoom={6}
        style={{ height: '100%', width: '100%', minHeight: 450, background: 'var(--bg-card)' }}
        zoomControl={true}
      >
        <TileLayer
          key={tileIdx}
          url={tiles.url}
          attribution={tiles.attribution}
          maxZoom={19}
          eventHandlers={{
            tileerror: () => setTileIdx(i => Math.min(i + 1, TILE_SOURCES.length - 1)),
          }}
        />

        <RecenterMap lat={lat} lon={lon} />
        <ResizeFix />
        <ClickHandler onMapClick={onMapClick} />

        {/* 14 Synoptic Airport METAR Markers */}
        {SYNOPTIC_STATIONS.map((st) => {
          const isSelected = Math.abs(st.lat - lat) < 0.2 && Math.abs(st.lon - lon) < 0.2;
          return (
            <Marker
              key={st.icao}
              position={[st.lat, st.lon]}
              icon={createStationIcon(st, isSelected)}
              eventHandlers={{
                click: () => {
                  onSelectStation?.(st);
                  onMapClick?.(st.lat, st.lon);
                },
              }}
            >
              <Popup>
                <div style={{ minWidth: 160 }}>
                  <div style={{ fontWeight: 800, fontSize: '0.9rem', display: 'flex', justifyContent: 'space-between' }}>
                    <span>{st.city}</span>
                    <span style={{ fontFamily: 'monospace', color: '#0284c7' }}>{st.icao}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: 2 }}>
                    {st.lat.toFixed(2)}°N, {st.lon.toFixed(2)}°E · 8,784 Obs
                  </div>
                  <div style={{ marginTop: 8, paddingTop: 6, borderTop: '1px solid #e2e8f0', fontSize: '0.78rem' }}>
                    <div>Raw NWP MAE: <strong>{st.mae.toFixed(2)}°C</strong></div>
                    {st.skill > 0 ? (
                      <div style={{ color: '#16a34a', fontWeight: 700, marginTop: 2 }}>
                        MOS Skill score: +{st.skill}% MAE
                      </div>
                    ) : (
                      <div style={{ color: '#64748b', marginTop: 2 }}>
                        NWP Dominant Regime
                      </div>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* User Selected Location Marker */}
        <Marker position={[lat, lon]} icon={defaultIcon}>
          <Popup>
            <div style={{ minWidth: 140 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: '0.8rem', color: '#666' }}>
                {lat.toFixed(4)}°N, {lon.toFixed(4)}°E
              </div>
              {currentTemp != null && (
                <div style={{ fontSize: '1.2rem', fontWeight: 700, marginTop: 4, color: '#f97316' }}>
                  {fmt.temp(currentTemp)}
                </div>
              )}
            </div>
          </Popup>
        </Marker>
      </MapContainer>
    </div>
  );
}
