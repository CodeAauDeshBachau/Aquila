'use client';
import React, { useEffect, useRef, useState } from 'react';
import { Search, MapPin, X } from 'lucide-react';

interface Location {
  name: string;
  coords: [number, number];
}

declare global {
  interface Window {
    L: any;
  }
}

export default function LandslideMonitoring() {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerRef = useRef<any>(null);
  const circleRef = useRef<any>(null);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [placeName, setPlaceName] = useState<string>('');
  const [coordinates, setCoordinates] = useState<string>('');
  const [location, setLocation] = useState<Location>({ name: 'Daunne', coords: [27.584, 83.843] });
  const [showForm, setShowForm] = useState<boolean>(false);
  const [mapReady, setMapReady] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window !== 'undefined' && window.L) {
      initializeMap();
      return;
    }

    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.css';
    document.head.appendChild(link);

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.js';
    script.async = true;

    script.onload = () => {
      initializeMap();
    };

    document.body.appendChild(script);

    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  const initializeMap = (): void => {
    if (mapRef.current && !mapInstanceRef.current && window.L) {
      const L = window.L;
      const map = L.map(mapRef.current, { attributionControl: false }).setView(location.coords, 10);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(map);

      const greenIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background-color: #16a34a; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });

      const marker = L.marker(location.coords, { icon: greenIcon })
        .addTo(map)
        .bindPopup(`<b>Monitoring Zone: ${location.name}</b><br>Coordinates: ${location.coords[0]}, ${location.coords[1]}`);

      const circle = L.circle(location.coords, {
        color: '#16a34a',
        fillColor: '#16a34a',
        fillOpacity: 0.15,
        radius: 8000
      }).addTo(map);

      markerRef.current = marker;
      circleRef.current = circle;
      mapInstanceRef.current = map;
      setMapReady(true);
    }
  };

  const updateLocation = (name: string, coords: [number, number]): void => {
    setLocation({ name, coords });

    if (mapInstanceRef.current && window.L) {
      const L = window.L;

      if (markerRef.current) {
        mapInstanceRef.current.removeLayer(markerRef.current);
      }
      if (circleRef.current) {
        mapInstanceRef.current.removeLayer(circleRef.current);
      }

      const greenIcon = L.divIcon({
        className: 'custom-marker',
        html: '<div style="background-color: #16a34a; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [30, 30],
        iconAnchor: [15, 15]
      });

      const marker = L.marker(coords, { icon: greenIcon })
        .addTo(mapInstanceRef.current)
        .bindPopup(`<b>Monitoring Zone: ${name}</b><br>Coordinates: ${coords[0]}, ${coords[1]}`);

      const circle = L.circle(coords, {
        color: '#16a34a',
        fillColor: '#16a34a',
        fillOpacity: 0.15,
        radius: 8000
      }).addTo(mapInstanceRef.current);

      markerRef.current = marker;
      circleRef.current = circle;

      mapInstanceRef.current.setView(coords, 10);
    }
  };

  const handleSetLocation = (): void => {
    if (placeName.trim() && coordinates.trim()) {
      const coordsArray = coordinates.split(',').map(c => parseFloat(c.trim()));

      if (coordsArray.length === 2 && !isNaN(coordsArray[0]) && !isNaN(coordsArray[1])) {
        updateLocation(placeName, [coordsArray[0], coordsArray[1]]);
        setShowForm(false);
        setPlaceName('');
        setCoordinates('');
      } else {
        alert('Please enter valid coordinates in format: latitude, longitude (e.g., 27.584, 83.843)');
      }
    } else {
      alert('Please fill in both place name and coordinates');
    }
  };

  const handleQuickLocation = (name: string, coords: [number, number]): void => {
    updateLocation(name, coords);
    setShowForm(false);
  };

  return (
    <div className="h-screen w-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200 relative">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-4">
            {/* Logo and Title */}
            <div className="flex items-center gap-3 min-w-0 flex-shrink-0">
              <div className="w-12 h-12 bg-green-700 rounded-full flex items-center justify-center flex-shrink-0">
                <MapPin className="w-6 h-6 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-xl font-semibold text-gray-900 truncate">
                  Landslide / Flood Monitoring : {location.name}
                </h1>
                <p className="text-sm text-gray-500 truncate">
                  Monitoring zone around {location.coords[0]}, {location.coords[1]}
                </p>
              </div>
            </div>

            {/* Set Location Button */}
            <button
              onClick={() => setShowForm(!showForm)}
              className="bg-green-600 hover:bg-green-700 hover:cursor-pointer text-white px-4 py-2 rounded-lg shadow-md text-sm font-medium transition-colors whitespace-nowrap flex-shrink-0"
            >
              {showForm ? 'Close Search' : 'Set Location'}
            </button>


          </div>
        </div>

        {/* Location Form Dropdown */}
        {showForm && (
          <div className="absolute top-full left-0 right-0 bg-white border-b border-gray-200 shadow-lg z-50">
            <div className="max-w-7xl mx-auto px-4 py-4">
              <div className="flex gap-6 items-start">
                {/* Form Inputs */}
                <div className="flex gap-4 flex-1">
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Place Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., Daunne"
                      value={placeName}
                      onChange={(e) => setPlaceName(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 text-gray-800 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    />
                  </div>
                  <div className="flex-1">
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      Coordinates (lat, lng)
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., 27.584, 83.843"
                      value={coordinates}
                      onChange={(e) => setCoordinates(e.target.value)}
                      className="w-full px-3 py-2 border text-gray-800 border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                    />
                  </div>
                  <div className="flex items-end">
                    <button
                      onClick={handleSetLocation}
                      className="bg-green-600 hover:bg-green-700 hover:cursor-pointer text-white px-6 py-2 rounded-md text-sm font-medium transition-colors"
                    >
                      Apply
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Map Container */}
      <div className="flex-1 relative">
        <div ref={mapRef} className="w-full h-full" style={{ position: 'relative', zIndex: 0 }} />

      </div>
    </div>
  );
}