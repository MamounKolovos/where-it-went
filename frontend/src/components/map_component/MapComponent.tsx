import { useEffect, useRef, useState, useCallback } from 'react';
import type { FC } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { socketService } from '@services/socket';
import { Place } from '@app-types/place';
import { SpendingData } from '@app-types/spending';
import { SpendingReport } from '@components/spending_report_component';
import ErrorBanner from '@components/map_component/ErrorBanner';
import LoadingIndicator from '@components/map_component/LoadingIndicator';
import MapControls from '@components/map_component/MapControls';
import './MapComponent.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || '';
if (MAPBOX_TOKEN) {
  mapboxgl.accessToken = MAPBOX_TOKEN;
}

// Default location: George Mason University
const DEFAULT_RADIUS = 500; // meters

// Calculate search radius based on zoom level
// This is based on S2 cell sizes in backend - Zoom 13 = 610m 
const calculateRadiusFromZoom = (zoom: number): number => {
  const baseRadius = 610; // S2 Level 13 radius
  const radius = Math.round(baseRadius * Math.pow(2, 13 - zoom));
  return Math.min(Math.max(radius, 10), 50000); // Clamp between 10m and 50km
};

interface MapComponentProps {
  initialLocation: { lat: number; lng: number } | null;
  startWithTracking?: boolean; 
}

const MapComponent: FC<MapComponentProps> = ({ initialLocation, startWithTracking = false }) => {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const markers = useRef<mapboxgl.Marker[]>([]);

  const [isReportVisible, setIsReportVisible] = useState(false);
  const [places, setPlaces] = useState<Place[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [exploreMode, setExploreMode] = useState(!startWithTracking); // If tracking allowed, start in Live Tracking mode
  const [spendingData, setSpendingData] = useState<SpendingData | null>(null);
  const [userLocation, setUserLocation] = useState<{ lat: number; lng: number } | null>(null);

  const clearMarkers = useCallback(() => {
    markers.current.forEach((marker) => marker.remove());
    markers.current = [];
  }, []);

  const fetchSpendingData = useCallback(async (place: Place) => {
    try {
      console.log(`[Map] Fetching spending data for: ${place.name}, ${place.state} ${place.zip_code}`);
      
      // Searching by recipient, state, and zip 
      const params = new URLSearchParams({
        recipient: place.name,
        state: place.state,
        zip: place.zip_code
      });
      const response = await fetch(`/search-spending-by-award?${params}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: SpendingData = await response.json();
      console.log(`[Map] Spending data response:`, data);
      console.log(`[Map] Found ${data.results.length} spending records`);
      setSpendingData(data);
      setIsReportVisible(true);
    } catch (error) {
      console.error('[Map] Error fetching spending data:', error);
      setError('Failed to load spending data for this location');
    }
  }, []);

  const addMarkerToMap = useCallback(
    (place: Place, isTarget: boolean = false) => {
      if (!map.current) return;

      const div = document.createElement('div');
      div.className = isTarget ? 'marker-target' : 'marker-place';
      div.style.width = '20px';
      div.style.height = '20px';
      div.style.background = isTarget ? '#ef4444' : '#3b82f6';
      div.style.borderRadius = '50%';
      div.style.border = '2px solid white';
      div.style.cursor = 'pointer';
      div.style.boxShadow = '0 2px 4px rgba(0,0,0,0.3)';

      const marker = new mapboxgl.Marker(div)
        .setLngLat([place.longitude, place.latitude])
        .addTo(map.current);

      if (isTarget) {
        div.addEventListener('click', () => setIsReportVisible(true));
      } else {
        const popup = new mapboxgl.Popup({ offset: 25 }).setHTML(
          `<div style="padding: 12px; min-width: 200px;">
            <strong style="font-size: 14px; color: #1a202c;">${place.name}</strong>
            <br/><small style="color: #718096;">${place.state} ${place.zip_code}</small>
            ${place.types.length > 0 ? `<br/><small style="color: #666;">${place.types[0]}</small>` : ''}
            <button id="spending-btn-${place.latitude}-${place.longitude}" 
                    style="margin-top: 10px; width: 100%; padding: 8px; background: #667eea; 
                           color: white; border: none; border-radius: 6px; cursor: pointer; 
                           font-weight: 600; font-size: 13px; transition: background 0.2s;"
                    onmouseover="this.style.background='#5568d3'" 
                    onmouseout="this.style.background='#667eea'">
              View Spending Report
            </button>
          </div>`
        );

        popup.on('open', () => {
          const btn = document.getElementById(`spending-btn-${place.latitude}-${place.longitude}`);
          btn?.addEventListener('click', () => fetchSpendingData(place));
        });
        
        marker.setPopup(popup);
      }

      markers.current.push(marker);
    },
    [fetchSpendingData]
  );


  const recenterMap = useCallback(() => {
    if (!map.current || !userLocation) return;
    
    map.current.flyTo({
      center: [userLocation.lng, userLocation.lat],
      zoom: 14,
      duration: 1000
    });
  }, [userLocation]);

  const fetchPlaces = useCallback(
    (latitude: number, longitude: number, customRadius?: number) => {
      setIsLoading(true);
      setError(null);
      setPlaces([]);
      clearMarkers();
      
      // Update tracked user location
      setUserLocation({ lat: latitude, lng: longitude });
      
      const radius = customRadius || DEFAULT_RADIUS;

      // Add marker for user's current location
      if (map.current) {
        const userMarker = document.createElement('div');
        userMarker.className = 'marker-user';
        userMarker.style.width = '24px';
        userMarker.style.height = '24px';
        userMarker.style.background = '#ef4444';
        userMarker.style.borderRadius = '50%';
        userMarker.style.border = '3px solid white';
        userMarker.style.boxShadow = '0 2px 8px rgba(0,0,0,0.4)';
        
        const marker = new mapboxgl.Marker(userMarker)
          .setLngLat([longitude, latitude])
          .setPopup(
            new mapboxgl.Popup({ offset: 25 }).setHTML(
              '<div style="padding: 8px;"><strong>Your Location</strong></div>'
            )
          )
          .addTo(map.current);
        
        markers.current.push(marker);
      }

      // Clean up old listeners before adding new ones
      socketService.removeAllListeners();
      
      socketService.connect();

      socketService.onPlacesUpdate((data) => {
        console.log('[Map] Received places update:', data.places.length);
        setPlaces((prev) => {
          const newPlaces = [...prev, ...data.places];
          
          // Add new markers
          data.places.forEach((place) => addMarkerToMap(place));
          
          return newPlaces;
        });
      });

      socketService.onPlacesComplete((data) => {
        console.log('[Map] Places streaming complete. Total:', data.total);
        setIsLoading(false);
      });

      socketService.onError((data) => {
        console.error('[Map] Socket error:', data.message);
        setError(data.message);
        setIsLoading(false);
      });

      // Emit location update to start streaming
      socketService.emitLocationUpdate({
        latitude,
        longitude,
        radius: radius,
      });
    },
    [clearMarkers, addMarkerToMap, exploreMode]
  );

    // Initialize map and load initial places
  useEffect(() => {
    if (map.current || !mapContainer.current || !initialLocation) return;

    if (!MAPBOX_TOKEN) {
      setError('Mapbox token not configured. Please check your .env file.');
      return;
    }

    map.current = new mapboxgl.Map({
      container: mapContainer.current,
      style: 'mapbox://styles/mapbox/streets-v12',
      center: [initialLocation.lng, initialLocation.lat],
      zoom: 14,
    });

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    map.current.on('load', () => {
      map.current!.flyTo({
        center: [initialLocation.lng, initialLocation.lat],
        zoom: 14,
        duration: 1500
      });
      fetchPlaces(initialLocation.lat, initialLocation.lng);
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [initialLocation, fetchPlaces]);

  // If in Explore mode, we update places as map moves with debounce
  useEffect(() => {
    if (!map.current || !exploreMode) return;

    let debounceTimeout: NodeJS.Timeout;

    const handleMoveEnd = () => {
      // Clear any existing timeout
      clearTimeout(debounceTimeout);
      
      // Wait 1 second after movement stops before fetching
      debounceTimeout = setTimeout(() => {
        const center = map.current!.getCenter();
        const zoom = map.current!.getZoom();
        const radius = calculateRadiusFromZoom(zoom);
        
        console.log(`[Explore Mode] Fetching places at (${center.lat.toFixed(6)}, ${center.lng.toFixed(6)}) with radius ${radius}m (zoom ${zoom.toFixed(1)})`);
        
        // Update user location marker to new center and fetch with calculated radius
        fetchPlaces(center.lat, center.lng, radius);
      }, 1000);
    };

    map.current.on('moveend', handleMoveEnd);

    return () => {
      clearTimeout(debounceTimeout);
      map.current?.off('moveend', handleMoveEnd);
    };
  }, [exploreMode, fetchPlaces, clearMarkers]);

  // Live Tracking mode: Track user's actual location
  useEffect(() => {
    if (exploreMode || !navigator.geolocation) return;

    console.log('[Map] Switching to Live Tracking mode');
    
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        console.log(`[Live Tracking] Position update: ${latitude}, ${longitude}`);
        
        // Calculate radius based on current zoom level
        if (map.current) {
          const zoom = map.current.getZoom();
          const radius = calculateRadiusFromZoom(zoom);
          console.log(`[Live Tracking] Using radius ${radius}m (zoom ${zoom.toFixed(1)})`);
          fetchPlaces(latitude, longitude, radius);
        } else {
          fetchPlaces(latitude, longitude);
        }
      },
      (error) => {
        console.error('[Live Tracking] Error:', error);
        setError('Unable to track location. Switching back to Explore mode.');
        setExploreMode(true);
      },
      {
        enableHighAccuracy: true,
        maximumAge: 30000,
        timeout: 27000
      }
    );

    return () => {
      navigator.geolocation.clearWatch(watchId);
      console.log('[Map] Stopped Live Tracking');
    };
  }, [exploreMode, fetchPlaces]);

  // Cleanup socket on unmount
  useEffect(() => {
    return () => {
      socketService.removeAllListeners();
      socketService.disconnect();
    };
  }, []);

  return (
    <div className="map-wrapper">
      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}
      
      {isLoading && <LoadingIndicator />}

      <MapControls
        placesCount={places.length}
        exploreMode={exploreMode}
        onToggleMode={() => setExploreMode(!exploreMode)}
        userLocation={userLocation}
        onRecenter={recenterMap}
      />

      <div ref={mapContainer} className="map-container" />

      {isReportVisible && spendingData && (
        <SpendingReport
          data={spendingData}
          onClose={() => {
            setIsReportVisible(false);
            setSpendingData(null);
          }}
        />
      )}
    </div>
  );
};

export default MapComponent;

