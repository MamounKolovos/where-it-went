import type { FC } from 'react';

interface MapControlsProps {
  placesCount: number;
  exploreMode: boolean;
  onToggleMode: () => void;
  userLocation: { lat: number; lng: number } | null;
  onRecenter: () => void;
}

const MapControls: FC<MapControlsProps> = ({
  placesCount,
  exploreMode,
  onToggleMode,
  userLocation,
  onRecenter,
}) => {
  return (
    <>
      {/* Map info and mode toggle */}
      <div className="map-info">
        <div className="places-count">
          {placesCount > 0 && `Found ${placesCount} places`}
        </div>
        <div className="mode-toggle-container">
          <span className="mode-label">Live Tracking</span>
          <button
            className="toggle-switch"
            onClick={onToggleMode}
            title={exploreMode ? 'Switch to Live Tracking' : 'Switch to Explore Mode'}
            aria-label="Toggle between Live Tracking and Explore Mode"
          >
            <span className={`toggle-slider ${!exploreMode ? 'active' : ''}`}></span>
          </button>
        </div>
      </div>

      {/* Recenter button - Google Maps style on right side */}
      {userLocation && (
        <button
          className="recenter-button"
          onClick={onRecenter}
          title="Recenter map to your location"
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#000000"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <circle cx="12" cy="12" r="3" />
            <line x1="12" y1="2" x2="12" y2="6" />
            <line x1="12" y1="18" x2="12" y2="22" />
            <line x1="2" y1="12" x2="6" y2="12" />
            <line x1="18" y1="12" x2="22" y2="12" />
          </svg>
        </button>
      )}
    </>
  );
};

export default MapControls;

