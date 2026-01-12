import { ChevronDown } from 'lucide-react';
import { FloodLocation } from '../types';
import { FLOOD_LOCATIONS } from '../constants/floodLocations';

interface LocationDropdownProps {
    selectedLocation: FloodLocation | null;
    showDropdown: boolean;
    setShowDropdown: (show: boolean) => void;
    onSelectLocation: (location: FloodLocation) => void;
}

export default function LocationDropdown({
    selectedLocation,
    showDropdown,
    setShowDropdown,
    onSelectLocation,
}: LocationDropdownProps) {
    return (
        <div className="relative">
            <button
                onClick={() => setShowDropdown(!showDropdown)}
                className="bg-white border border-gray-300 hover:border-gray-400 text-gray-700 px-4 py-2 rounded-lg shadow-sm text-sm font-medium transition-colors flex items-center gap-2 min-w-[180px] justify-between"
            >
                <span className="truncate">
                    {selectedLocation ? selectedLocation.location : 'Select Location'}
                </span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showDropdown ? 'rotate-180' : ''}`} />
            </button>

            {showDropdown && (
                <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 w-64 max-h-80 overflow-y-auto">
                    {FLOOD_LOCATIONS.map((loc) => (
                        <button
                            key={loc.id}
                            onClick={() => onSelectLocation(loc)}
                            className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors border-b border-gray-100 last:border-b-0 ${selectedLocation?.id === loc.id ? 'bg-green-50 text-green-700' : 'text-gray-700'
                                }`}
                        >
                            <div className="font-medium">{loc.location}</div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
