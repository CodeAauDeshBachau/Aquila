import { RefObject } from 'react';
import { FloodLocation, Mode, PredictionResponse } from '../types';
import MapInfoPanel from './MapInfoPanel';
import MapLegend from './MapLegend';

interface FloodMapProps {
    mapRef: RefObject<HTMLDivElement | null>;
    mode: Mode;
    selectedLocation: FloodLocation | null;
    customClickCoords: [number, number] | null;
    isSending: boolean;
    predictionResult: PredictionResponse | null;
    onMonitor: () => void;
    currentDate: string;
}

export default function FloodMap({
    mapRef,
    mode,
    selectedLocation,
    customClickCoords,
    isSending,
    predictionResult,
    onMonitor,
    currentDate,
}: FloodMapProps) {
    return (
        <div className="flex-1 relative">
            <div ref={mapRef} className="w-full h-full" style={{ position: 'relative', zIndex: 0 }} />

            <MapInfoPanel
                mode={mode}
                selectedLocation={selectedLocation}
                customClickCoords={customClickCoords}
                isSending={isSending}
                predictionResult={predictionResult}
                onMonitor={onMonitor}
                currentDate={currentDate}
            />

            <MapLegend />
        </div>
    );
}
