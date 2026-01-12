import { MapPin } from 'lucide-react';
import { FloodLocation, Mode } from '../types';
import LocationDropdown from './LocationDropdown';
import ModeToggle from './ModeToggle';

interface HeaderProps {
    selectedLocation: FloodLocation | null;
    mode: Mode;
    setMode: (mode: Mode) => void;
    showDropdown: boolean;
    setShowDropdown: (show: boolean) => void;
    onSelectLocation: (location: FloodLocation) => void;
}

export default function Header({
    selectedLocation,
    mode,
    setMode,
    showDropdown,
    setShowDropdown,
    onSelectLocation,
}: HeaderProps) {
    return (
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
                                Flood Monitoring {selectedLocation ? `: ${selectedLocation.location}` : ''}
                            </h1>
                            <p className="text-sm text-gray-500 truncate">
                                {selectedLocation
                                    ? `Monitoring area: ${selectedLocation.coords[0].toFixed(4)}, ${selectedLocation.coords[1].toFixed(4)}`
                                    : 'Select a location from the map or dropdown to begin monitoring'}
                            </p>
                        </div>
                    </div>

                    {/* Location Dropdown and Mode Toggle */}
                    <div className="flex items-center gap-3 flex-shrink-0">
                        {/* Location Dropdown */}
                        <LocationDropdown
                            selectedLocation={selectedLocation}
                            showDropdown={showDropdown}
                            setShowDropdown={setShowDropdown}
                            onSelectLocation={onSelectLocation}
                        />

                        {/* Mode Toggle */}
                        <ModeToggle mode={mode} setMode={setMode} />
                    </div>
                </div>
            </div>
        </div>
    );
}
