import { MapPinned, Activity, AlertTriangle, Calendar } from 'lucide-react';
import { FloodLocation, Mode, PredictionResponse } from '../types';

interface MapInfoPanelProps {
    mode: Mode;
    selectedLocation: FloodLocation | null;
    customClickCoords: [number, number] | null;
    isSending: boolean;
    predictionResult: PredictionResponse | null;
    onMonitor: () => void;
    currentDate: string;
}

export default function MapInfoPanel({
    mode,
    selectedLocation,
    customClickCoords,
    isSending,
    predictionResult,
    onMonitor,
    currentDate,
}: MapInfoPanelProps) {
    const hasLocation = selectedLocation || customClickCoords;

    // Use location's custom date if available, otherwise use real-time date
    const displayDate = selectedLocation?.date || currentDate;

    return (
        <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg z-10 transition-all duration-300 w-80 max-h-[75vh] flex flex-col overflow-hidden">
            {/* Header - Fixed */}
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between bg-gradient-to-r from-green-50 to-emerald-50">
                <p className="text-sm font-medium text-gray-700">
                    Mode: <span className="text-green-700 font-semibold capitalize">{mode}</span>
                </p>
            </div>

            {/* Scrollable Content */}
            <div className="flex-1 overflow-y-auto px-4 py-3 custom-scrollbar">

                {selectedLocation && (
                    <div className="pb-2 border-b border-gray-200">
                        <p className="text-xs text-gray-600">
                            <span className="font-medium">Selected:</span> {selectedLocation.location}
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                            Lat: {selectedLocation.coords[0].toFixed(4)}, Lng: {selectedLocation.coords[1].toFixed(4)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Date: {displayDate}
                        </p>
                    </div>
                )}

                {customClickCoords && (
                    <div className="pb-2 border-b border-gray-200">
                        <p className="text-xs text-gray-600 flex items-center gap-1">
                            <MapPinned className="w-3 h-3 text-amber-500" />
                            <span className="font-medium">Custom Location</span>
                        </p>
                        <p className="text-xs text-gray-500 mt-1">
                            Lat: {customClickCoords[0].toFixed(6)}
                        </p>
                        <p className="text-xs text-gray-500">
                            Lng: {customClickCoords[1].toFixed(6)}
                        </p>
                        <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                            <Calendar className="w-3 h-3" />
                            Date: {currentDate}
                        </p>
                    </div>
                )}

                {/* Monitor Button */}
                {hasLocation && (
                    <button
                        onClick={onMonitor}
                        disabled={isSending}
                        className={`mt-3 w-full py-2 px-4 hover:cursor-pointer rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2 ${isSending
                            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                            : 'bg-green-600 hover:bg-green-700 text-white'
                            }`}
                    >
                        <Activity className={`w-4 h-4 ${isSending ? 'animate-pulse' : ''}`} />
                        {isSending ? 'Processing...' : 'Monitor'}
                    </button>
                )}

                {/* Prediction Results */}
                {predictionResult && (
                    <div className="mt-3 pt-3 border-t border-gray-200 bg-blue-50 rounded-lg p-3">
                        <p className="text-xs font-semibold text-blue-800 flex items-center gap-1 mb-2">
                            <Activity className="w-3 h-3" />
                            Prediction Result
                        </p>
                        <div className="space-y-1">
                            <p className="text-xs text-blue-700">
                                <span className="font-medium">Status:</span>{' '}
                                <span className={predictionResult.prediction.prediction === 'Flood' ? 'text-red-600 font-bold' : 'text-green-600 font-bold'}>
                                    {predictionResult.prediction.prediction}
                                </span>
                            </p>
                            <p className="text-xs text-blue-700">
                                <span className="font-medium">Probability:</span>{' '}
                                {(predictionResult.prediction.flood_probability * 100).toFixed(1)}%
                            </p>
                            <p className="text-xs text-blue-700">
                                <span className="font-medium">Confidence:</span>{' '}
                                {predictionResult.prediction.confidence}
                            </p>
                            <p className="text-xs text-blue-700">
                                <span className="font-medium">Risk Level:</span>{' '}
                                {predictionResult.prediction.risk_level}
                            </p>
                            <div className="mt-2 p-2 bg-amber-100 rounded text-xs text-amber-800 flex items-start gap-1">
                                <AlertTriangle className="w-3 h-3 mt-0.5 flex-shrink-0" />
                                <span>{predictionResult.prediction.recommendation}</span>
                            </div>
                        </div>
                    </div>
                )}

                {!selectedLocation && !customClickCoords && (
                    <p className="text-xs text-gray-500 mt-2">
                        Click a marker, use dropdown, or click anywhere on the map
                    </p>
                )}

            </div>
            {/* End of scrollable content */}
        </div>
    );
}
