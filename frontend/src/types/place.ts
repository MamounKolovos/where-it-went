export interface Place {
  name: string;
  latitude: number;
  longitude: number;
  state: string;
  zip_code: string;
  types: string[];
}

export interface LocationUpdate {
  latitude: number;
  longitude: number;
  radius: number;
}

export interface PlacesUpdateEvent {
  places: Place[];
}

export interface PlacesCompleteEvent {
  total: number;
}

export interface ErrorEvent {
  message: string;
}

