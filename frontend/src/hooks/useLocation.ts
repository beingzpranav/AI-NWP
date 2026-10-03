import { useState, useCallback } from 'react';

interface Coords { lat: number; lon: number; label: string; }

// Default: New Delhi
const DEFAULT: Coords = { lat: 28.6139, lon: 77.2090, label: 'New Delhi, India' };

export function useLocationState() {
  const [coords, setCoords] = useState<Coords>(DEFAULT);

  const setLocation = useCallback((lat: number, lon: number, label: string) => {
    setCoords({ lat, lon, label });
  }, []);

  const detectLocation = useCallback(() => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      pos => setCoords({
        lat: pos.coords.latitude,
        lon: pos.coords.longitude,
        label: 'My Location',
      }),
      () => setCoords(DEFAULT)
    );
  }, []);

  return { coords, setLocation, detectLocation };
}
