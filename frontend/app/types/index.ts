export interface FloodLocation {
    id: number;
    location: string;
    coords: [number, number]; // [lat, lng] - center of bounding box
    bounds: [[number, number], [number, number]]; // [[lat_min, lon_min], [lat_max, lon_max]]
    date?: string; // Optional custom date for API request (YYYY-MM-DD format)
    color?: string; // Optional custom marker color (hex)
}

export type Mode = 'prediction' | 'detection';

export interface PredictionData {
    flood_probability: number;
    prediction: string;
    confidence: string;
    recommendation: string;
    risk_level: string;
}

export interface PredictionResponse {
    lat: number;
    long: number;
    date_str: string;
    prediction: PredictionData;
}

export interface DetectionImages {
    sar: string | null;           // Sentinel-1 SAR (VV)
    permanent_water: string | null; // Permanent Water mask
    model_water: string | null;   // Model Water Detection
    classification: string | null; // Classification Map
    flood_only: string | null;    // New Flood Only
}

export interface DetectionResponse {
    success: boolean;
    flood_detected: boolean;
    message: string;
    image: string | null; // Legacy: Base64 encoded RGB PNG image (single)
    images: DetectionImages | null; // New: 5-panel images dictionary
    sar_date: string | null;
    date_selection_reason: string | null;
}

declare global {
    interface Window {
        L: any;
    }
}
