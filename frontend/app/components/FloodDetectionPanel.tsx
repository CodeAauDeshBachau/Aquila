'use client';
import { useState } from 'react';
import { X } from 'lucide-react';
import { DetectionResponse } from '../types';

interface FloodDetectionPanelProps {
    detectionResult: DetectionResponse;
    onClose: () => void;
    locationName?: string;
    coordinates?: [number, number];
}

interface ImagePanelData {
    id: string;
    key: keyof NonNullable<DetectionResponse['images']>;
    title: string;
    shortTitle: string;
}

const IMAGE_PANELS: ImagePanelData[] = [
    { id: 'A', key: 'sar', title: 'Sentinel-1 SAR (VV)', shortTitle: 'SAR' },
    { id: 'B', key: 'permanent_water', title: 'Permanent Water', shortTitle: 'Water Mask' },
    { id: 'C', key: 'model_water', title: 'Model Water Detection', shortTitle: 'Model Detection' },
    { id: 'D', key: 'classification', title: 'Classification Map', shortTitle: 'Classification' },
    { id: 'E', key: 'flood_only', title: 'New Flood Only', shortTitle: 'Flood' }
];

export default function FloodDetectionPanel({
    detectionResult,
    onClose,
    locationName,
    coordinates
}: FloodDetectionPanelProps) {
    const [selectedImage, setSelectedImage] = useState<ImagePanelData | null>(null);

    const hasImages = detectionResult.images && Object.values(detectionResult.images).some(img => img !== null);

    const handleImageClick = (panel: ImagePanelData) => {
        if (detectionResult.images?.[panel.key]) {
            setSelectedImage(panel);
        }
    };

    return (
        <>
            {/* Enlarged Image Modal */}
            {selectedImage && detectionResult.images?.[selectedImage.key] && (
                <div
                    className="fixed inset-0 bg-black/80 z-[100] flex items-center justify-center p-4"
                    onClick={() => setSelectedImage(null)}
                >
                    <div
                        className="relative bg-white rounded-lg p-4 max-w-4xl w-full"
                        onClick={e => e.stopPropagation()}
                    >
                        <div className="flex items-center justify-between mb-3">
                            <h3 className="text-gray-800 font-medium">
                                {selectedImage.id}: {selectedImage.title}
                            </h3>
                            <button
                                onClick={() => setSelectedImage(null)}
                                className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <img
                            src={`data:image/png;base64,${detectionResult.images[selectedImage.key]}`}
                            alt={selectedImage.title}
                            className="w-full h-auto rounded border border-gray-300"
                            style={{ maxHeight: '70vh', objectFit: 'contain' }}
                        />
                    </div>
                </div>
            )}

            {/* Main Panel */}
            <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 sm:p-6">
                <div className="bg-white rounded-lg shadow-xl w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden">

                    {/* Header */}
                    <div className="px-5 py-4 border-b border-gray-200 flex items-center justify-between bg-gray-50">
                        <div>
                            <h2 className="text-lg font-semibold text-gray-800">Flood Detection Results</h2>
                            {locationName && (
                                <p className="text-sm text-gray-500">{locationName}</p>
                            )}
                        </div>
                        <button
                            onClick={onClose}
                            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-200 rounded transition-colors"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Status */}
                    <div className={`px-5 py-3 border-b ${detectionResult.flood_detected
                        ? 'bg-red-50 border-red-100'
                        : 'bg-green-50 border-green-100'
                        }`}>
                        <div className="flex items-center justify-between">
                            <div>
                                <span className={`font-semibold ${detectionResult.flood_detected ? 'text-red-700' : 'text-green-700'
                                    }`}>
                                    {detectionResult.flood_detected ? 'Flood Detected' : 'No Flood Detected'}
                                </span>
                                <p className={`text-sm ${detectionResult.flood_detected ? 'text-red-600' : 'text-green-600'
                                    }`}>
                                    {detectionResult.message}
                                </p>
                            </div>
                            {coordinates && (
                                <span className="text-sm text-gray-500">
                                    {coordinates[0].toFixed(4)}, {coordinates[1].toFixed(4)}
                                </span>
                            )}
                        </div>
                    </div>

                    {/* Content */}
                    <div className="flex-1 overflow-y-auto p-5 custom-scrollbar">

                        {/* 5-Panel Grid */}
                        {hasImages && (
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 mb-5">
                                {IMAGE_PANELS.map((panel) => {
                                    const imageData = detectionResult.images?.[panel.key];
                                    return (
                                        <div
                                            key={panel.id}
                                            className={`rounded-lg border overflow-hidden ${imageData
                                                ? 'border-gray-300 hover:border-green-500 cursor-pointer'
                                                : 'border-gray-200 opacity-50'
                                                }`}
                                            onClick={() => handleImageClick(panel)}
                                        >
                                            <div className="px-2 py-1.5 bg-gray-100 border-b border-gray-200">
                                                <div className="flex items-center gap-1.5">
                                                    <span className="bg-green-700 text-white text-xs font-medium px-1.5 py-0.5 rounded">
                                                        {panel.id}
                                                    </span>
                                                    <span className="text-xs font-medium text-gray-700 truncate">
                                                        {panel.shortTitle}
                                                    </span>
                                                </div>
                                            </div>
                                            <div className="aspect-square bg-gray-800">
                                                {imageData ? (
                                                    <img
                                                        src={`data:image/png;base64,${imageData}`}
                                                        alt={panel.title}
                                                        className="w-full h-full object-contain"
                                                    />
                                                ) : (
                                                    <div className="w-full h-full flex items-center justify-center text-gray-500 text-xs">
                                                        No data
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        )}

                        {/* Fallback single image */}
                        {!hasImages && detectionResult.image && (
                            <div className="mb-5">
                                <div className="bg-gray-800 p-3 rounded-lg">
                                    <img
                                        src={`data:image/png;base64,${detectionResult.image}`}
                                        alt="Flood Detection Result"
                                        className="w-full max-w-xl mx-auto rounded"
                                    />
                                </div>
                            </div>
                        )}

                        {/* Date Info */}
                        {detectionResult.date_selection_reason && (
                            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 mb-4 text-sm">
                                <span className="font-medium text-gray-700">Date Info: </span>
                                <span className="text-gray-600">
                                    {detectionResult.date_selection_reason.replace(/\s*\(Note:.*?\)/gi, '')}
                                </span>
                            </div>
                        )}

                        {/* Legend */}
                        <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                            <p className="text-sm font-medium text-gray-700 mb-2">Legend</p>
                            <div className="flex flex-wrap gap-4 text-sm">
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#808080' }} />
                                    <span className="text-gray-600">Land</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#0064C8' }} />
                                    <span className="text-gray-600">Permanent Water</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 rounded" style={{ backgroundColor: '#C83232' }} />
                                    <span className="text-gray-600">Flood</span>
                                </div>
                            </div>
                        </div>

                        <p className="text-xs text-gray-400 text-center mt-3">
                            256 × 256 pixels · 10m resolution
                        </p>
                    </div>
                </div>
            </div>
        </>
    );
}
