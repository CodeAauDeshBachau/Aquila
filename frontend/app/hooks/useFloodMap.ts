'use client';
import { useEffect, useRef, useState, useCallback } from 'react';
import { FloodLocation, Mode, PredictionResponse, DetectionResponse } from '../types';
import { FLOOD_LOCATIONS } from '../constants/floodLocations';

export function useFloodMap() {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstanceRef = useRef<any>(null);
    const markersRef = useRef<any[]>([]);
    const selectedMarkerRef = useRef<any>(null);
    const boundsRectRef = useRef<any>(null);
    const customMarkerRef = useRef<any>(null);

    const [selectedLocation, setSelectedLocation] = useState<FloodLocation | null>(null);
    const [mapReady, setMapReady] = useState<boolean>(false);
    const [mode, setMode] = useState<Mode>('prediction');
    const [showDropdown, setShowDropdown] = useState<boolean>(false);
    const [customClickCoords, setCustomClickCoords] = useState<[number, number] | null>(null);
    const [isSending, setIsSending] = useState<boolean>(false);
    const [predictionResult, setPredictionResult] = useState<PredictionResponse | null>(null);
    const [detectionResult, setDetectionResult] = useState<DetectionResponse | null>(null);

    // Function to toggle mode and clear previous results
    const handleModeChange = useCallback((newMode: Mode) => {
        setMode(newMode);
        // Clear results when mode changes
        setPredictionResult(null);
        setDetectionResult(null);
    }, []);




    // Backend API URLs - configure in .env.local
    const PREDICTION_API_URL = process.env.NEXT_PUBLIC_PREDICTION_API_URL || 'http://127.0.0.1:8000/predict';
    const DETECTION_API_URL = process.env.NEXT_PUBLIC_DETECTION_API_URL || 'http://127.0.0.1:8000/flood/detect';

    // Get current date in YYYY-MM-DD format
    const getCurrentDate = (): string => {
        const today = new Date();
        return today.toISOString().split('T')[0];
    };

    // Get date for API request - use location's custom date if available
    const getDateForLocation = useCallback((location: FloodLocation | null): string => {
        if (location?.date) {
            return location.date;
        }
        return getCurrentDate();
    }, []);










    // Function to send request to prediction model
    const sendPredictionRequest = useCallback(async (
        lat: number,
        lng: number,
        customDate?: string
    ): Promise<PredictionResponse | null> => {
        try {
            const dateStr = customDate || getCurrentDate();
            const url = `${PREDICTION_API_URL}/${lat.toFixed(6)}/${lng.toFixed(6)}/${dateStr}`;

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                throw new Error('Failed to get prediction');
            }

            const data: PredictionResponse = await response.json();
            console.log('Prediction response:', data);
            return data;
        } catch (error) {
            console.error('Error getting prediction:', error);
            return null;
        }
    }, [PREDICTION_API_URL]);





    // Function to send request to detection model (SAR-based flood detection)
    const sendDetectionRequest = useCallback(async (
        lat: number,
        lng: number,
        customDate?: string
    ): Promise<DetectionResponse | null> => {
        try {

            let url = `${DETECTION_API_URL}/${lat.toFixed(6)}/${lng.toFixed(6)}`;
            if (customDate) {
                url += `?target_date=${customDate}`;
            }
            console.log('Calling Detection API:', url);

            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                },
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.log('API error response:', url, response.status, errorText);
                console.error('API error:', errorText);
                throw new Error(`API Error: ${response.status} - ${errorText}`);
            }

            const data: DetectionResponse = await response.json();
            console.log('Detection response:', data);
            return data;
        } catch (error) {
            console.error('Error getting detection:', error);
            return null;
        }
    }, [DETECTION_API_URL]);





    // Function to send coordinates based on current mode
    const sendCoordinatesToBackend = useCallback(async (
        lat: number,
        lng: number,
        customDate?: string
    ): Promise<void> => {
        setIsSending(true);
        setPredictionResult(null);
        setDetectionResult(null);

        try {
            if (mode === 'prediction') {
                const result = await sendPredictionRequest(lat, lng, customDate);
                if (result) {
                    setPredictionResult(result);
                }
            } else {
                const result = await sendDetectionRequest(lat, lng, customDate);
                if (result) {
                    setDetectionResult(result);
                }
            }
        } finally {
            setIsSending(false);
        }
    }, [mode, sendPredictionRequest, sendDetectionRequest]);

    const initializeMap = useCallback((): void => {
        if (mapRef.current && !mapInstanceRef.current && window.L) {
            const L = window.L;
            const map = L.map(mapRef.current, { attributionControl: false }).setView([20, 0], 2);

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                maxZoom: 19
            }).addTo(map);

            const defaultIcon = L.divIcon({
                className: 'custom-marker',
                html: '<div style="background-color: #3b82f6; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); cursor: pointer;"></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });

            FLOOD_LOCATIONS.forEach((loc) => {
                const markerColor = loc.color || '#3b82f6';
                const locationIcon = L.divIcon({
                    className: 'custom-marker',
                    html: `<div style="background-color: ${markerColor}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); cursor: pointer;"></div>`,
                    iconSize: [24, 24],
                    iconAnchor: [12, 12]
                });

                const marker = L.marker(loc.coords, { icon: locationIcon })
                    .addTo(map)
                    .bindPopup(`
            <b>${loc.location}</b><br>
            <span style="font-size: 12px; color: #666;">
            ${loc.date ? `Date: ${loc.date}<br>` : ''}Click on "Monitor" button
            </span>
            `);

                marker.on('click', () => {
                    selectLocation(loc);
                });

                markersRef.current.push({ marker, location: loc, originalColor: loc.color || '#3b82f6' });
            });

            mapInstanceRef.current = map;
            setMapReady(true);

            map.on('click', (e: any) => {
                const { lat, lng } = e.latlng;
                handleMapClick(lat, lng);
            });
        }
    }, []);





    const handleMapClick = useCallback((lat: number, lng: number): void => {
        if (!mapInstanceRef.current || !window.L) return;

        const L = window.L;

        setSelectedLocation(null);
        setCustomClickCoords([lat, lng]);

        // Restore original colors for all markers
        markersRef.current.forEach(({ marker, originalColor }) => {
            const color = originalColor || '#3b82f6';
            const defaultIcon = L.divIcon({
                className: 'custom-marker',
                html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); cursor: pointer;"></div>`,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            marker.setIcon(defaultIcon);
        });

        if (customMarkerRef.current) {
            mapInstanceRef.current.removeLayer(customMarkerRef.current);
        }
        if (boundsRectRef.current) {
            mapInstanceRef.current.removeLayer(boundsRectRef.current);
        }

        const customIcon = L.divIcon({
            className: 'custom-marker',
            html: '<div style="background-color: #f59e0b; width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.4); cursor: pointer;"></div>',
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });

        const marker = L.marker([lat, lng], { icon: customIcon })
            .addTo(mapInstanceRef.current)
            .bindPopup(`
        <b>Custom Location</b><br>
        <span style="font-size: 12px; color: #666;">
        Lat: ${lat.toFixed(6)}<br>
        Lng: ${lng.toFixed(6)}
        </span>
        `)
            .openPopup();

        customMarkerRef.current = marker;
    }, []);



    const selectLocation = useCallback((loc: FloodLocation): void => {
        setSelectedLocation(loc);
        setShowDropdown(false);
        setCustomClickCoords(null);

        // Clear previous results when selecting new location
        setPredictionResult(null);
        setDetectionResult(null);

        if (mapInstanceRef.current && window.L) {
            const L = window.L;

            if (customMarkerRef.current) {
                mapInstanceRef.current.removeLayer(customMarkerRef.current);
                customMarkerRef.current = null;
            }

            const selectedIcon = L.divIcon({
                className: 'custom-marker',
                html: '<div style="background-color: #16a34a; width: 30px; height: 30px; border-radius: 50%; border: 3px solid white; box-shadow: 0 4px 8px rgba(0,0,0,0.4); cursor: pointer;"></div>',
                iconSize: [30, 30],
                iconAnchor: [15, 15]
            });

            markersRef.current.forEach(({ marker, location, originalColor }) => {
                if (location.id === loc.id) {
                    marker.setIcon(selectedIcon);
                    selectedMarkerRef.current = marker;
                } else {
                    // Restore the original color for non-selected markers
                    const color = originalColor || '#3b82f6';
                    const defaultIcon = L.divIcon({
                        className: 'custom-marker',
                        html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3); cursor: pointer;"></div>`,
                        iconSize: [24, 24],
                        iconAnchor: [12, 12]
                    });
                    marker.setIcon(defaultIcon);
                }
            });

            if (boundsRectRef.current) {
                mapInstanceRef.current.removeLayer(boundsRectRef.current);
            }

            // Fixed radius of 2.5 km (2500 meters)
            const fixedRadius = 2500;

            const circle = L.circle(loc.coords, {
                color: '#16a34a',
                fillColor: '#16a34a',
                fillOpacity: 0.15,
                weight: 2,
                radius: fixedRadius
            }).addTo(mapInstanceRef.current);

            boundsRectRef.current = circle;

            mapInstanceRef.current.fitBounds(circle.getBounds(), { padding: [50, 50] });
        }
    }, [sendCoordinatesToBackend]);

    const selectRandomLocation = useCallback((): void => {
        const randomIndex = Math.floor(Math.random() * FLOOD_LOCATIONS.length);
        const randomLocation = FLOOD_LOCATIONS[randomIndex];

        if (customMarkerRef.current && mapInstanceRef.current) {
            mapInstanceRef.current.removeLayer(customMarkerRef.current);
            customMarkerRef.current = null;
        }
        setCustomClickCoords(null);

        selectLocation(randomLocation);
    }, [selectLocation]);

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
    }, [initializeMap]);

    // Function to clear detection result
    const clearDetectionResult = useCallback(() => {
        setDetectionResult(null);
    }, []);

    return {
        mapRef,
        selectedLocation,
        mapReady,
        mode,
        setMode: handleModeChange,
        showDropdown,
        setShowDropdown,
        customClickCoords,
        isSending,
        predictionResult,
        detectionResult,
        selectLocation,
        selectRandomLocation,
        monitorLocation: sendCoordinatesToBackend,
        clearDetectionResult,
    };
}
