import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Suspense, lazy } from 'react';
import Navbar from './components/Navbar';
import LoadingState from './components/LoadingState';

// Lazy-load pages for better initial load performance
const Dashboard    = lazy(() => import('./pages/Dashboard'));
const ForecastPage = lazy(() => import('./pages/ForecastPage'));
const ModelsPage   = lazy(() => import('./pages/ModelsPage'));
const MapPage      = lazy(() => import('./pages/MapPage'));
const PipelinePage = lazy(() => import('./pages/PipelinePage'));

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <Navbar />
        <main style={{ flex: 1, paddingTop: 60 }}>
          <Suspense fallback={<LoadingState message="Loading page…" />}>
            <Routes>
              <Route path="/"          element={<Dashboard />} />
              <Route path="/forecast"  element={<ForecastPage />} />
              <Route path="/models"    element={<ModelsPage />} />
              <Route path="/map"       element={<MapPage />} />
              <Route path="/pipeline"  element={<PipelinePage />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </BrowserRouter>
  );
}
