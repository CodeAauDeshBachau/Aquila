import React from 'react';

export default function MapLegend() {
    return (
        <div className="absolute bottom-4 left-4 bg-white px-4 py-3 rounded-lg shadow-md z-10">
            <div className="flex items-center gap-2 text-xs text-gray-600">
                <div className="w-4 h-4 rounded-full bg-blue-500 border-2 border-white shadow"></div>
                <span>Available Location</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                <div className="w-4 h-4 rounded-full bg-green-600 border-2 border-white shadow"></div>
                <span>Selected Location</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                <div className="w-4 h-4 rounded-full bg-amber-500 border-2 border-white shadow"></div>
                <span>Custom Click Location</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-600 mt-1">
                <div className="w-4 h-4 rounded-full bg-green-600 bg-opacity-20 border border-green-600"></div>
                <span>Monitoring Area</span>
            </div>
        </div>
    );
}
