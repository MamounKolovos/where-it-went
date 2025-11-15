import { useState, useRef, useEffect } from 'react';
import type { FC } from 'react';
import { Place } from '@app-types/place';

interface SearchResult {
  display_name: {
    name: string;
    language_code?: string | null;
  };
  location: {
    latitude: number;
    longitude: number;
  };
  types: string[];
  formatted_address: string;
  address_components: Array<{
    long_text: string;
    short_text?: string | null;
    types: string[];
  }>;
}

interface SearchBarProps {
  onMoveToLocation: (lat: number, lng: number) => void;
  onViewSpendingReport: (place: Place) => void;
  exploreMode: boolean;
}

const SearchBar: FC<SearchBarProps> = ({ onMoveToLocation, onViewSpendingReport, exploreMode }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestion, setSuggestion] = useState<string>('');
  const [isUpdatingResults, setIsUpdatingResults] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const autoSearchTimerRef = useRef<NodeJS.Timeout | null>(null);
  const currentExpectedQueryRef = useRef<string>('');
  const currentSearchQueryRef = useRef<string>('');

  // Close results when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setShowResults(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (autoSearchTimerRef.current) {
        clearTimeout(autoSearchTimerRef.current);
      }
    };
  }, []);

  const fetchAutocomplete = async (query: string) => {
    const trimmedQuery = query.trim();
    
    if (!trimmedQuery) {
      setSuggestion('');
      currentExpectedQueryRef.current = '';
      setIsUpdatingResults(false); // Clear loading state
      return;
    }

    // Minimum query length to avoid unnecessary/error-prone requests
    if (trimmedQuery.length < 3) {
      setSuggestion('');
      currentExpectedQueryRef.current = '';
      setIsUpdatingResults(false); // Clear loading state
      return;
    }

    // Update the expected query for this request
    currentExpectedQueryRef.current = trimmedQuery;

    try {
      const response = await fetch('/api/autocomplete', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input: trimmedQuery,
        }),
      });

      // Check if this response is still relevant (query hasn't changed)
      // Use ref to get the most current value, not stale state
      const currentQuery = currentSearchQueryRef.current.trim();
      if (currentQuery !== trimmedQuery) {
        // Query has changed, ignore this response
        return;
      }

      if (!response.ok) {
        // Only process error if query still matches
        if (currentQuery === trimmedQuery && response.status !== 400) {
          // Log non-400 errors only if still relevant
          console.error('Autocomplete error:', response.statusText);
        }
        return;
      }

      // Double-check query still matches before processing response
      if (currentSearchQueryRef.current.trim() !== trimmedQuery) {
        return;
      }

      const data = await response.json();
      const newSuggestion = data.suggestion || '';
      
      // check if query still matches before setting suggestion
      // Use ref to ensure we're checking against the latest value
      if (currentSearchQueryRef.current.trim() === trimmedQuery && currentExpectedQueryRef.current === trimmedQuery) {
        setSuggestion(newSuggestion);

        // If we got a suggestion, set up auto-search after 2 seconds
        if (newSuggestion) {
          // Clear any existing auto-search timer
          if (autoSearchTimerRef.current) {
            clearTimeout(autoSearchTimerRef.current);
          }

          // Set new auto-search timer
          autoSearchTimerRef.current = setTimeout(() => {
            // check before auto-searching - use ref for current value
            if (currentSearchQueryRef.current.trim() === trimmedQuery && currentExpectedQueryRef.current === trimmedQuery) {
              console.log('[Auto-search] Triggering search for:', newSuggestion);
              performSearch(newSuggestion);
            }
          }, 1000);
        }
      }
    } catch (err) {
      // Check if this error is still relevant - use ref for current value
      const currentQuery = currentSearchQueryRef.current.trim();
      if (currentQuery !== trimmedQuery) {
        // Query has changed, ignore this error
        return;
      }
      // Silently ignore all errors - network errors, 400s, etc.
      // Don't log anything to avoid console spam
      setSuggestion('');
    }
  };

  const handleInputChange = (value: string) => {
    setSearchQuery(value);
    // Update ref immediately so it's always current
    currentSearchQueryRef.current = value;
    
    // Clear existing timers
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }
    // Cancel auto-search when user continues typing
    if (autoSearchTimerRef.current) {
      clearTimeout(autoSearchTimerRef.current);
      autoSearchTimerRef.current = null;
    }

    // Clear suggestion when user types
    setSuggestion('');
    
    // Clear expected query when user types (so old responses are ignored)
    // We'll set it again when we make the actual request
    currentExpectedQueryRef.current = '';

    // Mark that we're updating (if results are already visible and query is not empty)
    if (showResults && value.trim().length > 0) {
      setIsUpdatingResults(true);
    } else {
      // Clear updating state if input is empty
      setIsUpdatingResults(false);
    }

    // Set new timer for autocomplete (500ms debounce)
    debounceTimerRef.current = setTimeout(() => {
      // Get the CURRENT value from ref, which is always up-to-date
      const currentValue = currentSearchQueryRef.current.trim();
      if (currentValue.length >= 3) {
        fetchAutocomplete(currentValue);
      } else {
        // Clear updating state if query is too short
        setIsUpdatingResults(false);
      }
    }, 500);
  };

  const performSearch = async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      return;
    }

    setIsSearching(true);
    setIsUpdatingResults(false);
    setError(null);

    try {
      const response = await fetch('/api/text-search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text_query: query,
        }),
      });

      if (!response.ok) {
        throw new Error(`Search failed: ${response.statusText}`);
      }

      const data = await response.json();
      setSearchResults(data.places || []);
      setShowResults(true);
    } catch (err) {
      console.error('Search error:', err);
      setError('Failed to search locations. Please try again.');
      setSearchResults([]);
    } finally {
      setIsSearching(false);
      setIsUpdatingResults(false); // Clear updating state when search completes
    }
  };

  const handleSearch = async () => {
    // Cancel any pending auto-search
    if (autoSearchTimerRef.current) {
      clearTimeout(autoSearchTimerRef.current);
    }
    
    // Use current search query
    await performSearch(searchQuery);
  };

  const acceptSuggestion = () => {
    if (suggestion) {
      setSearchQuery(suggestion);
      setSuggestion('');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Tab' && suggestion) {
      e.preventDefault(); // Prevent default tab behavior
      acceptSuggestion();
    } else if (e.key === 'Enter') {
      // Cancel any pending auto-search and search immediately
      if (autoSearchTimerRef.current) {
        clearTimeout(autoSearchTimerRef.current);
      }
      handleSearch();
    } else if (e.key === 'ArrowRight' && suggestion && searchQuery) {
      // Allow right arrow to also accept suggestion if cursor is at end
      const input = e.currentTarget as HTMLInputElement;
      if (input.selectionStart === searchQuery.length) {
        e.preventDefault();
        acceptSuggestion();
      }
    }
  };

  const convertToPlace = (result: SearchResult): Place => {
    // Extract state and zip from address components
    let state = '';
    let zipCode = '';

    result.address_components.forEach((component) => {
      if (component.types.includes('administrative_area_level_1')) {
        state = component.short_text || component.long_text;
      }
      if (component.types.includes('postal_code')) {
        zipCode = component.long_text;
      }
    });

    return {
      name: result.display_name.name,
      latitude: result.location.latitude,
      longitude: result.location.longitude,
      types: result.types,
      state: state,
      zip_code: zipCode,
    };
  };

  const handleMoveToResult = (result: SearchResult) => {
    onMoveToLocation(result.location.latitude, result.location.longitude);
    setShowResults(false);
    setSearchQuery('');
  };

  const handleViewReport = (result: SearchResult) => {
    const place = convertToPlace(result);
    onViewSpendingReport(place);
    setShowResults(false);
  };

  const getPlaceIcon = (types: string[]) => {
    if (types.includes('university') || types.includes('school')) return '🎓';
    if (types.includes('hospital') || types.includes('health')) return '🏥';
    if (types.includes('government')) return '🏛️';
    if (types.includes('airport')) return '✈️';
    if (types.includes('city_hall') || types.includes('local_government_office')) return '🏛️';
    if (types.includes('library')) return '📚';
    if (types.includes('park')) return '🌳';
    if (types.includes('museum')) return '🏛️';
    if (types.includes('stadium')) return '🏟️';
    return '📍';
  };

  // Get the suggestion overlay text (only the part after what user typed)
  const getSuggestionOverlay = () => {
    if (!suggestion || !searchQuery) return '';
    if (suggestion.toLowerCase().startsWith(searchQuery.toLowerCase())) {
      return suggestion.slice(searchQuery.length);
    }
    return '';
  };

  return (
    <div className="search-bar-container" ref={searchRef}>
      <div className="search-input-wrapper">
        <span className="search-icon">🔍</span>
        <div className="search-input-container">
          <input
            type="text"
            className="search-input"
            placeholder="Search                                                     "
            value={searchQuery}
            onChange={(e) => handleInputChange(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => searchResults.length > 0 && setShowResults(true)}
          />
          {getSuggestionOverlay() && (
            <div 
              className="search-suggestion-overlay"
              onClick={acceptSuggestion}
              onTouchEnd={(e) => {
                e.preventDefault();
                acceptSuggestion();
              }}
            >
              <span className="search-suggestion-typed">{searchQuery}</span>
              <span className="search-suggestion-text">{getSuggestionOverlay()}</span>
            </div>
          )}
        </div>
        {searchQuery && (
          <button
            className="clear-search-button"
            onClick={() => {
              setSearchQuery('');
              setSearchResults([]);
              setShowResults(false);
              setSuggestion('');
            }}
            title="Clear search"
          >
            ✕
          </button>
        )}
        <button
          className="search-button"
          onClick={handleSearch}
          disabled={isSearching || !searchQuery.trim()}
        >
          {isSearching ? '...' : 'Search'}
        </button>
      </div>

      {error && (
        <div className="search-error">
          {error}
        </div>
      )}

      {showResults && searchResults.length > 0 && (
        <div className="search-results">
          {isUpdatingResults && (
            <div className="search-updating-banner">
              <span className="loading-spinner"></span>
              <span>Loading...</span>
            </div>
          )}
          {searchResults.map((result, index) => (
            <div key={index} className="search-result-item">
              <div className="search-result-info">
                <span className="search-result-icon">{getPlaceIcon(result.types)}</span>
                <div className="search-result-details">
                  <div className="search-result-name">{result.display_name.name}</div>
                  <div className="search-result-address">{result.formatted_address}</div>
                  {result.types.length > 0 && (
                    <div className="search-result-type">{result.types[0].replace(/_/g, ' ')}</div>
                  )}
                </div>
              </div>
              <div className="search-result-actions">
                <button
                  className="search-action-button move-to"
                  onClick={() => handleMoveToResult(result)}
                  disabled={!exploreMode}
                  title={exploreMode ? "Move to this location" : "Switch to explore mode to fly to other places"}
                >
                  Fly To
                </button>
                <button
                  className="search-action-button view-report"
                  onClick={() => handleViewReport(result)}
                  title="View spending report"
                >
                  View Report
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showResults && searchResults.length === 0 && !isSearching && searchQuery && (
        <div className="search-results">
          <div className="search-no-results">
            No locations found for "{searchQuery}"
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchBar;

