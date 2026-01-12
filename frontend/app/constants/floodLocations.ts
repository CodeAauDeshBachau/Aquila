import { FloodLocation } from '../types';

// Pre-defined flood monitoring locations from Sen1Floods11 dataset
export const FLOOD_LOCATIONS: FloodLocation[] = [
    { id: 1, location: 'Bolivia', coords: [-13.675143, -64.998950], bounds: [[-15.959245, -65.636263], [-11.391042, -64.361636]] },
    { id: 12, location: 'Colombia', coords: [4.605932, -67.847957], bounds: [[2.110187, -68.996948], [7.101677, -66.698966]] },
    { id: 2, location: 'Ghana', coords: [9.120137, -1.042854], bounds: [[6.305931, -2.303238], [11.934343, 0.217529]] },
    { id: 3, location: 'India', coords: [26.565948, 93.156902], bounds: [[24.847137, 92.150652], [28.284759, 94.163352]] },
    { id: 4, location: 'Cambodia', coords: [12.423059, 105.251065], bounds: [[10.571214, 104.075347], [14.274904, 106.426783]] },
    { id: 5, location: 'Nigeria', coords: [7.326974, 5.740953], bounds: [[4.117742, 4.536895], [10.536205, 6.945012]] },
    { id: 6, location: 'Pakistan', coords: [31.196834, 70.771838], bounds: [[28.042944, 68.992796], [34.350723, 72.550881]] },
    { id: 7, location: 'Paraguay', coords: [-24.913021, -56.619016], bounds: [[-28.187202, -58.588000], [-21.638841, -54.650031]] },
    { id: 8, location: 'Somalia', coords: [3.927749, 45.394701], bounds: [[1.308621, 44.205151], [6.546877, 46.584251]] },
    { id: 9, location: 'Spain', coords: [38.537692, 0.054752], bounds: [[37.662834, -1.111557], [39.412550, 1.221062]] },
    { id: 10, location: 'Sri-Lanka', coords: [7.461362, 81.112345], bounds: [[5.136162, 80.132911], [9.786561, 82.091780]] },
    { id: 11, location: 'USA', coords: [39.709791, -95.027249], bounds: [[38.357816, -95.691763], [41.061767, -94.362736]] },

    // Additional test location
    { id: 99, location: 'Test Location (Nepal)', coords: [27.806678, 84.905390], bounds: [[27.706678, 84.805390], [27.906678, 85.005390]], date: '2024-09-29', color: '#ef4444' },
    { id: 100, location: 'Test Location ', coords: [27.706175, 84.422958], bounds: [[27.606175, 84.322958], [27.806175, 84.522958]], date: '2024-09-28', color: '#8f46e5' },
];
