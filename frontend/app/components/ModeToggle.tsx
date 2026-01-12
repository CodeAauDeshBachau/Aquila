import React from 'react';
import { Mode } from '../types';

interface ModeToggleProps {
    mode: Mode;
    setMode: (mode: Mode) => void;
}

export default function ModeToggle({ mode, setMode }: ModeToggleProps) {
    return (
        <div className="bg-gray-100 rounded-lg p-1 flex gap-1">
            <button
                onClick={() => setMode('prediction')}
                className={`px-4 py-2 rounded-md text-sm font-medium hover:cursor-pointer transition-colors ${mode === 'prediction'
                    ? 'bg-white text-green-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                    }`}
            >
                Prediction
            </button>
            <button
                onClick={() => setMode('detection')}
                className={`px-4 py-2 rounded-md text-sm font-medium  hover:cursor-pointer transition-colors ${mode === 'detection'
                    ? 'bg-white text-green-700 shadow-sm'
                    : 'text-gray-600 hover:text-gray-900'
                    }`}
            >
                Detection
            </button>
        </div>
    );
}
