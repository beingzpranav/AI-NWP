import { useQuery } from '@tanstack/react-query';
import {
  getForecastByCoords,
  getCurrentConditions,
  getWeatherUnionStatus,
  getLocations,
  getModelWeights,
  getModelComparison,
  getMultiCityVerification,
  getHealth,
} from '../services/api';

export const useForecast = (lat: number, lon: number, hours = 48) =>
  useQuery({
    queryKey: ['forecast', lat, lon, hours],
    queryFn: () => getForecastByCoords(lat, lon, hours),
    staleTime: 5 * 60 * 1000,   // 5 min
    retry: 2,
    enabled: !!lat && !!lon,
  });

export const useCurrentConditions = (lat: number, lon: number) =>
  useQuery({
    queryKey: ['current', lat, lon],
    queryFn: () => getCurrentConditions(lat, lon),
    staleTime: 3 * 60 * 1000,   // 3 min
    refetchInterval: 5 * 60 * 1000,
    enabled: !!lat && !!lon,
  });

export const useWeatherUnionStatus = (lat?: number, lon?: number) =>
  useQuery({
    queryKey: ['wu-status'],   // no lat/lon in key — always tests global connectivity
    queryFn: () => getWeatherUnionStatus(), // no coords — backend picks best test city
    staleTime: 60 * 1000,
    retry: 1,
  });

export const useLocations = () =>
  useQuery({
    queryKey: ['locations'],
    queryFn: getLocations,
    staleTime: 10 * 60 * 1000,
  });

export const useModelWeights = () =>
  useQuery({
    queryKey: ['model-weights'],
    queryFn: getModelWeights,
    staleTime: 2 * 60 * 1000,
    refetchInterval: 2 * 60 * 1000,
  });

export const useModelComparison = () =>
  useQuery({
    queryKey: ['model-comparison'],
    queryFn: getModelComparison,
    staleTime: 5 * 60 * 1000,
  });

export const useMultiCityVerification = () =>
  useQuery({
    queryKey: ['multi-city-verification'],
    queryFn: getMultiCityVerification,
    staleTime: 5 * 60 * 1000,
  });

export const useHealth = () =>
  useQuery({
    queryKey: ['health'],
    queryFn: getHealth,
    staleTime: 30 * 1000,
    refetchInterval: 60 * 1000,
  });
