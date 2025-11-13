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
          <span style={{ color: '#ef4444', fontSize: '20px' }}>▲</span>
        </button>
      )}
    </>
  );
};

export default MapControls;

