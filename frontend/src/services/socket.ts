import { io, Socket } from 'socket.io-client';
import {
  LocationUpdate,
  PlacesUpdateEvent,
  PlacesCompleteEvent,
  ErrorEvent,
} from '@app-types/place';

const SOCKET_URL = import.meta.env.VITE_SOCKET_URL || 'http://localhost:5000';

class SocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;

  connect(): Socket {
    // Return existing socket if it exists (connected or connecting)
    if (this.socket) {
      return this.socket;
    }

    this.socket = io(`${SOCKET_URL}/dev`, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.socket.on('connect', () => {
      console.log('[Socket] Connected to backend');
      this.reconnectAttempts = 0;
    });

    this.socket.on('disconnect', (reason: string) => {
      console.log('[Socket] Disconnected:', reason);
    });

    this.socket.on('connect_error', (error: Error) => {
      console.error('[Socket] Connection error:', error);
      this.reconnectAttempts++;
      
      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('[Socket] Max reconnection attempts reached');
      }
    });

    return this.socket;
  }

  disconnect(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
  }

  emitLocationUpdate(location: LocationUpdate): void {
    if (!this.socket) {
      console.error('[Socket] Socket not initialized');
      return;
    }

    if (this.socket.connected) {
      this.socket.emit('location_update', location);
    } else {
      // Wait for connection before emitting
      console.log('[Socket] Waiting for connection before emitting...');
      this.socket.once('connect', () => {
        console.log('[Socket] Now connected, emitting location update');
        this.socket!.emit('location_update', location);
      });
    }
  }

  onPlacesUpdate(callback: (data: PlacesUpdateEvent) => void): void {
    this.socket?.on('places_update', callback);
  }

  onPlacesComplete(callback: (data: PlacesCompleteEvent) => void): void {
    this.socket?.on('places_complete', callback);
  }

  onError(callback: (data: ErrorEvent) => void): void {
    this.socket?.on('error', callback);
  }

  removeAllListeners(): void {
    // Only remove our custom event listeners, not Socket.IO internal ones
    this.socket?.off('places_update');
    this.socket?.off('places_complete');
    this.socket?.off('error');
  }
}

export const socketService = new SocketService();

