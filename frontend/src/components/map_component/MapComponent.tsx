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
import { circle as turfCircle } from "@turf/turf";
import './MapComponent.css';

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN || '';
if (MAPBOX_TOKEN) {
  mapboxgl.accessToken = MAPBOX_TOKEN;
}

// Default location: George Mason University
const DEFAULT_LAT = 38.832352857203624;
const DEFAULT_LNG = -77.31284409452543;
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
  const [mapTheme, setMapTheme] = useState<"light" | "dark">("light");
  const [isThemeTransitioning, setIsThemeTransitioning] = useState(false);
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
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
      Math.sin(dLng / 2) * Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
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

      const markerElement = document.createElement('div');
      markerElement.className = isTarget ? 'marker-target' : 'marker-place';


      const img = document.createElement('img');

      img.src = '/landmark-icon.png';
      img.style.width = '32px';
      img.style.height = '32px';
      img.style.cursor = 'pointer';
      img.style.filter = 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))';
      img.alt = place.name || 'Place marker';
      img.onerror = () => {
        console.error('[Map] Failed to load landmark icon, using fallback');
        // Fallback code
        markerElement.style.width = '20px';
        markerElement.style.height = '20px';
        markerElement.style.background = '#3b82f6';
        markerElement.style.borderRadius = '50%';
        markerElement.style.border = '2px solid white';
        markerElement.style.cursor = 'pointer';
        markerElement.style.boxShadow = '0 2px 4px rgba(25, 21, 21, 0.3)';
      };
      markerElement.appendChild(img);

      const marker = new mapboxgl.Marker(markerElement)
        .setLngLat([place.longitude, place.latitude])
        .addTo(map.current);

      if (isTarget) {
        markerElement.addEventListener('click', () => setIsReportVisible(true));
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

  //blue cicle around the user

  const updateRadiusCircle = (
    mapInstance: mapboxgl.Map,
    center: { lat: number; lng: number },
    radiusMeters: number
  ) => {
    // Only add layers if map is loaded
    if (!mapInstance.isStyleLoaded()) {
      console.warn('[Map] Map style not loaded yet, skipping radius circle');
      return;
    }

    try {
      const sourceId = "user-radius-source";
      const fillLayerId = "user-radius-fill";
      const outlineLayerId = "user-radius-outline";

      const circleFeature = turfCircle([center.lng, center.lat], radiusMeters / 1000, {
        steps: 64,
        units: "kilometers",
      });

      const data = {
        type: "FeatureCollection",
        features: [circleFeature],
      };

      // Update if source already exists
      const existing = mapInstance.getSource(sourceId) as mapboxgl.GeoJSONSource | undefined;
      if (existing) {
        existing.setData(data as GeoJSON.FeatureCollection);
        return;
      }

      // Otherwise create source + layers
      mapInstance.addSource(sourceId, {
        type: "geojson",
        data: data as GeoJSON.FeatureCollection,
      });

      mapInstance.addLayer({
        id: fillLayerId,
        type: "fill",
        source: sourceId,
        paint: {
          "fill-color": "rgba(0, 122, 255, 0.15)",
          "fill-outline-color": "transparent",
        },
      });

      mapInstance.addLayer({
        id: outlineLayerId,
        type: "line",
        source: sourceId,
        paint: {
          "line-color": "#007AFF",
          "line-width": 2,
        },
      });
    } catch (error) {
      console.error('[Map] Error updating radius circle:', error);
    }
  };


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
      // Only update circle if map is loaded and ready
      if (map.current && map.current.isStyleLoaded()) {
        updateRadiusCircle(map.current, { lat: latitude, lng: longitude }, radius);
      } else if (map.current) {
        // Wait for map to load before adding circle
        map.current.once('load', () => {
          updateRadiusCircle(map.current!, { lat: latitude, lng: longitude }, radius);
        });
      }

      // Add marker for user's current location
      if (map.current) {
        const userMarker = document.createElement('div');
        userMarker.className = 'google-location-dot';
        const ring = document.createElement('div');
        ring.className = 'pulse-ring';
        userMarker.appendChild(ring);

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


        data.places.forEach((place) => {
          console.log(`[Map] Adding marker for: ${place.name}`);
          addMarkerToMap(place);
        });

                setPlaces((prev) => [...prev, ...data.places]);
      });

      socketService.onPlacesComplete((data) => {
      
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

    
      socketService.emitLocationUpdate({
        latitude,
        longitude,
        radius: radius,
      });
    },
    [clearMarkers, addMarkerToMap, exploreMode]
  );

  useEffect(() => {
    if (map.current || !mapContainer.current) {
      console.log('[Map] Skipping initialization:', { hasMap: !!map.current, hasContainer: !!mapContainer.current });
      return;
    }

    if (!MAPBOX_TOKEN) {
      setError('Mapbox token not configured. Please check your .env file.');
      return;
    }

  
    const location = initialLocation || { lat: DEFAULT_LAT, lng: DEFAULT_LNG };
    console.log('[Map] Initializing map with location:', location);

    //  style based on theme
    const initialStyle = mapTheme === "light"
      ? "mapbox://styles/mapbox/streets-v11"

      : "mapbox://styles/mapbox/dark-v11";

    try {
      map.current = new mapboxgl.Map({
        container: mapContainer.current,
        style: initialStyle,
        center: [location.lng, location.lat],
        zoom: 14,
      });
      console.log('[Map] Map instance created with style:', initialStyle);
    } catch (error) {
      console.error('[Map] Error creating map:', error);
      setError('Failed to initialize map. Please check your Mapbox token.');
      return;
    }

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    map.current.on('load', () => {
      console.log('[Map] Map loaded successfully');
      map.current!.flyTo({
        center: [location.lng, location.lat],
        zoom: 14,
        duration: 1500
      });
      // Fetch places on load for both modes (after a small delay to ensure map is fully ready)
      setTimeout(() => {
        const initialRadius = calculateRadiusFromZoom(14);
        fetchPlaces(location.lat, location.lng, initialRadius); // pyright: ignore[reportUnknownVariableType]
      }, 100);
    });

    return () => {
      map.current?.remove();
      map.current = null;
    };
  }, [initialLocation, fetchPlaces, exploreMode, mapTheme]);

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
        updateRadiusCircle(map.current!, { lat: center.lat, lng: center.lng }, radius);

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
          updateRadiusCircle(map.current!, { lat: latitude, lng: longitude }, radius);
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

        updateRadiusCircle(
          map.current!,
          lastFetchPosition.current,
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

  // Update map style when theme changes
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) {
      console.log('[Map] Map not ready for theme change');
      return;
    }

    const styleUrl =
      mapTheme === "light"
        ? "mapbox://styles/mapbox/light-v11"
        : "mapbox://styles/mapbox/dark-v11";

    console.log('[Map] Changing theme to:', mapTheme, 'Style URL:', styleUrl);

    // Start transition
    setIsThemeTransitioning(true);

    try {
      // Fade out the map smoothly
      if (mapContainer.current) {
        mapContainer.current.style.transition = 'opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1)';
        // Use requestAnimationFrame to ensure transition is applied
        requestAnimationFrame(() => {
          if (mapContainer.current) {
            mapContainer.current.style.opacity = '0.4';
          }
        });
      }

      // Wait for fade out, then change style
      setTimeout(() => {
        if (!map.current) return;

        // Change the style
        map.current.setStyle(styleUrl);

        // When style is applied, fade back in and re-add the radius circle
        map.current.once("styledata", () => {
          console.log('[Map] Style data loaded, re-adding radius circle');

          // Wait a bit for tiles to start loading, then fade in
          setTimeout(() => {
            if (mapContainer.current) {
              mapContainer.current.style.opacity = '1';
            }
            // Remove overlay after fade in completes
            setTimeout(() => {
              setIsThemeTransitioning(false);
            }, 300);
          }, 150);

          if (userLocation && map.current) {
            const zoom = map.current.getZoom();
            const radius = calculateRadiusFromZoom(zoom);
            updateRadiusCircle(map.current, userLocation, radius);
          }
        });
      }, 250);
    } catch (error) {
      console.error('[Map] Error changing theme:', error);
      setIsThemeTransitioning(false);
      if (mapContainer.current) {
        mapContainer.current.style.opacity = '1';
      }
    }
  }, [mapTheme, userLocation]);

  const toggleTheme = () => {
    setMapTheme(prev => (prev === "light" ? "dark" : "light"));
  };

  return (
    <div className="map-wrapper">
      {error && <ErrorBanner message={error} onClose={() => setError(null)} />}

      {isLoading && <LoadingIndicator />}

      {/* Theme transition overlay */}
      {isThemeTransitioning && (
        <div className="theme-transition-overlay" />
      )}

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

      <button
        onClick={toggleTheme}
        className="theme-toggle-button"
        title={mapTheme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
        aria-label={mapTheme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
      >
        {mapTheme === "light" ? (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        )}
      </button>


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

