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
import SearchBar from '@components/map_component/SearchBar';
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
  return Math.min(Math.max(radius, 10), 156000); // Clamp between 10m and 156km - supports S2 level 5
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
  const requestIdRef = useRef<number>(0); // Track request ID to ignore old updates
  const lastFetchPosition = useRef<{ lat: number; lng: number } | null>(null); // Last position where we fetched data
  const zoomDebounceRef = useRef<NodeJS.Timeout | null>(null); // Debounce timer for zoom changes

  const clearMarkers = useCallback(() => {
    markers.current.forEach((marker) => marker.remove());
    markers.current = [];
  }, []);

  // Calculate distance between two points in meters (Haversine formula)
  const getDistance = useCallback((lat1: number, lng1: number, lat2: number, lng2: number): number => {
    const R = 6371000; // Earth radius in meters
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
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

  const moveToLocation = useCallback((lat: number, lng: number) => {
    if (!map.current) return;

    // Fly to the new location with smooth animation
    // Note: In Live Tracking mode, the Fly To button is disabled
    // User must manually switch to Explore Mode to use this feature
    map.current.flyTo({
      center: [lng, lat],
      zoom: 14,
      duration: 1500
    });

    // Explore mode will automatically fetch places after the fly animation
  }, [exploreMode]);

  const handleSearchSpendingReport = useCallback((place: Place) => {
    fetchSpendingData(place);
  }, [fetchSpendingData]);

  const fetchPlaces = useCallback(
    (latitude: number, longitude: number, customRadius?: number) => {
      // Increment request ID to track this new request
      requestIdRef.current += 1;
      const currentRequestId = requestIdRef.current;
      
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
        // Ignore updates from old requests
        if (requestIdRef.current !== currentRequestId) {
          console.log(`[Map] Ignoring update from old request (current: ${requestIdRef.current}, received: ${currentRequestId})`);
          return;
        }
        
        console.log(`[Map] STREAMING: Received ${data.places.length} places (request ${currentRequestId})`);
        
        // Add markers immediately for visual feedback
        data.places.forEach((place) => {
          console.log(`[Map] Adding marker for: ${place.name}`);
          addMarkerToMap(place);
        });
        
        // Update state
        setPlaces((prev) => [...prev, ...data.places]);
      });

      socketService.onPlacesComplete((data) => {
        // Ignore completion from old requests
        if (requestIdRef.current !== currentRequestId) {
          console.log('[Map] Ignoring completion from old request');
          return;
        }
        
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
      // Only fetch on load if we are not in explore mode
      if (!exploreMode) {
        const initialRadius = calculateRadiusFromZoom(14);
        fetchPlaces(initialLocation.lat, initialLocation.lng, initialRadius); // pyright: ignore[reportUnknownVariableType]
      }
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [initialLocation, fetchPlaces, exploreMode]);

  // If in Explore mode, we update places as map moves with debounce
  useEffect(() => {
    if (!map.current || !exploreMode) return;

    console.log('[Map] Switching to Explore Mode');

    // Immediately fetch places at current map center when switching to Explore Mode
    const center = map.current.getCenter();
    const zoom = map.current.getZoom();
    const radius = calculateRadiusFromZoom(zoom);
    console.log(`[Explore Mode] Initial fetch at (${center.lat.toFixed(6)}, ${center.lng.toFixed(6)})`);
    fetchPlaces(center.lat, center.lng, radius);

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
    lastFetchPosition.current = null; // Reset on mode switch
    
    const watchId = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        console.log(`[Live Tracking] Position update: ${latitude}, ${longitude}`);
        
        // Always smoothly pan camera to follow user
        if (map.current) {
          map.current.panTo([longitude, latitude], {
            duration: 500  // Smooth 0.5s pan animation
          });
        }

        // Calculate if we should fetch new data
        let shouldFetch = false;
        
        if (!lastFetchPosition.current) {
          // First position - always fetch
          shouldFetch = true;
          console.log('[Live Tracking] First position - fetching data');
        } else {
          // Check if moved significantly (>20m)
          const distance = getDistance(
            lastFetchPosition.current.lat,
            lastFetchPosition.current.lng,
            latitude,
            longitude
          );
          
          if (distance > 20) {
            shouldFetch = true;
            console.log(`[Live Tracking] Moved ${distance.toFixed(1)}m - fetching new data`);
          } else {
            console.log(`[Live Tracking] Moved only ${distance.toFixed(1)}m - skipping fetch`);
          }
        }
        
        // Fetch places if moved significantly
        if (shouldFetch && map.current) {
          const zoom = map.current.getZoom();
          const radius = calculateRadiusFromZoom(zoom);
          fetchPlaces(latitude, longitude, radius);
          lastFetchPosition.current = { lat: latitude, lng: longitude };
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

    // Handle zoom changes with debouncing
    const handleZoomEnd = () => {
      if (!map.current || !lastFetchPosition.current) return;
      
      // Clear existing timer
      if (zoomDebounceRef.current) {
        clearTimeout(zoomDebounceRef.current);
      }
      
      // Wait 500ms after zoom stops before fetching
      zoomDebounceRef.current = setTimeout(() => {
        if (!map.current || !lastFetchPosition.current) return;
        
        const zoom = map.current.getZoom();
        const radius = calculateRadiusFromZoom(zoom);
        console.log(`[Live Tracking] Zoom changed - fetching with new radius ${radius}m`);
        
        fetchPlaces(
          lastFetchPosition.current.lat,
          lastFetchPosition.current.lng,
          radius
        );
      }, 500);
    };

    map.current?.on('zoomend', handleZoomEnd);

    return () => {
      navigator.geolocation.clearWatch(watchId);
      if (zoomDebounceRef.current) {
        clearTimeout(zoomDebounceRef.current);
      }
      map.current?.off('zoomend', handleZoomEnd);
      console.log('[Map] Stopped Live Tracking');
    };
  }, [exploreMode, fetchPlaces, getDistance]);

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

      <SearchBar
        onMoveToLocation={moveToLocation}
        onViewSpendingReport={handleSearchSpendingReport}
        exploreMode={exploreMode}
      />

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

