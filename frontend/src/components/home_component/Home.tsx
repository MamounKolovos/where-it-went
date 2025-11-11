import { useState } from 'react';
import type { FC } from 'react';
import MapComponent from '@components/map_component';
import './Home.css';

// Default location: George Mason University
const DEFAULT_LAT = 38.832352857203624;
const DEFAULT_LNG = -77.31284409452543;

const Home: FC = () => {
  const [showWelcome, setShowWelcome] = useState(true);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [isLoadingLocation, setIsLoadingLocation] = useState(false);
  const [userAllowedLocation, setUserAllowedLocation] = useState(false);

  const handleAllowAccess = () => {
    if (!navigator.geolocation) {
      console.warn('Geolocation not supported, using default location');
      setUserLocation({ lat: DEFAULT_LAT, lng: DEFAULT_LNG });
      setShowWelcome(false);
      return;
    }

    setIsLoadingLocation(true);
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        console.log(`[Home] Got user location: ${latitude}, ${longitude}`);
        setUserLocation({ lat: latitude, lng: longitude });
        setUserAllowedLocation(true); // User allowed location access
        setShowWelcome(false);
        setIsLoadingLocation(false);
      },
      (error) => {
        console.error('[Home] Geolocation error:', error);
        console.log('[Home] Using default location');
        setUserLocation({ lat: DEFAULT_LAT, lng: DEFAULT_LNG });
        setShowWelcome(false);
        setIsLoadingLocation(false);
      }
    );
  };

  const handleSkip = () => {
    console.log('[Home] User skipped location access, using default');
    setUserLocation({ lat: DEFAULT_LAT, lng: DEFAULT_LNG });
    setShowWelcome(false);
  };

  if (showWelcome) {
    return (
      <div className="welcome-screen">
        <div className="welcome-content">
          <h1>Where It Went</h1>
          <p className="tagline">
            Track Federal Spending Across America
          </p>
          <p className="description">
            Explore government spending data mapped to real locations. 
            See where your tax dollars are going in real-time.
          </p>
          
          {isLoadingLocation ? (
            <div className="loading-location">
              <div className="spinner"></div>
              <p>Getting your location...</p>
            </div>
          ) : (
            <div className="welcome-actions">
              <button className="btn-primary" onClick={handleAllowAccess}>
                Allow Location Access
              </button>
              <button className="btn-secondary" onClick={handleSkip}>
                Explore Without Location
              </button>
            </div>
          )}
          
          <p className="default-info">
            Default location: George Mason University, Virginia
          </p>
        </div>
      </div>
    );
  }

  return <MapComponent initialLocation={userLocation} startWithTracking={userAllowedLocation} />;
};

export default Home;

