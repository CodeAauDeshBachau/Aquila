import numpy as np
import datetime
import requests
import io
from typing import Optional, Tuple
import tifffile

from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    MimeType,
    CRS,
    BBox,
    DataCollection
)

from .config import get_settings


class SentinelDataService:
    """Service for fetching Sentinel-1 SAR data via Sentinel Hub."""
    
    def __init__(self):
        self.settings = get_settings()
        self.config = SHConfig()
        self.config.sh_client_id = self.settings.SH_CLIENT_ID
        self.config.sh_client_secret = self.settings.SH_CLIENT_SECRET
        self.sar_date = None  # Track which date was selected
        self.date_selection_reason = None
        
    def get_sentinel1_data(self, lat: float, lon: float, target_date: Optional[datetime.date] = None, days_back: int = 12) -> Optional[np.ndarray]:
        """
        Fetch Sentinel-1 VV/VH data for a location.
        If target_date is provided, searches within ±15 days of that date (respecting 12-day revisit time).
        Otherwise fetches the most recent image from past 12 days.
        Returns numpy array (256, 256, 2) with VV and VH bands in dB, or None.
        Sets self.sar_date and self.date_selection_reason for tracking.
        """
        radius = self.settings.BUFFER_RADIUS
        
        # Calculate bounding box
        lat_delta = radius / 111132.954
        lon_delta = radius / (111132.954 * np.cos(np.radians(lat)))
        bbox = BBox(
            bbox=[lon - lon_delta, lat - lat_delta, lon + lon_delta, lat + lat_delta],
            crs=CRS.WGS84,
        )
        
        # Determine date range
        today = datetime.date.today()
        if target_date:
            # Don't allow future dates
            if target_date > today:
                self.sar_date = None
                self.date_selection_reason = f"NO SAR for that timeframe"
                print(f"DEBUG: {self.date_selection_reason}")
                return None
            
            # Search around target date (±15 days, accounting for 12-day Sentinel-1 revisit time)
            start_date = (target_date - datetime.timedelta(days=15)).isoformat()
            end_date = (target_date + datetime.timedelta(days=15)).isoformat()
            search_mode = "nearest"
            search_description = f"within ±15 days of {target_date.isoformat()}"
        else:
            # Default: fetch latest from past 12 days (Sentinel-1 revisit time)
            end_date = today.isoformat()
            start_date = (today - datetime.timedelta(days=days_back)).isoformat()
            search_mode = "latest"
            search_description = f"latest from past {days_back} days"
        
        # Evalscript for VV and VH bands
        evalscript = """
        //VERSION=3
        function setup() {
          return {
            input: ["VV", "VH"],
            output: { bands: 2, sampleType: "FLOAT32" }
          };
        }
        function evaluatePixel(sample) {
          let vv_db = 10 * Math.log(Math.max(sample.VV, 1e-5)) / Math.LN10;
          let vh_db = 10 * Math.log(Math.max(sample.VH, 1e-5)) / Math.LN10;
          return [vv_db, vh_db];
        }
        """
        
        # Use mostRecent for latest, or leave default for nearest
        mosaicking_order = "mostRecent" if search_mode == "latest" else None
        
        request = SentinelHubRequest(
            evalscript=evalscript,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=DataCollection.SENTINEL1_IW,
                    time_interval=(start_date, end_date),
                    mosaicking_order=mosaicking_order,
                )
            ],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=bbox,
            size=(self.settings.IMAGE_SIZE, self.settings.IMAGE_SIZE),
            config=self.config,
        )
        
        try:
            data = request.get_data()
            if data:
                # Set date tracking info - be honest about limitations
                self.sar_date = None  # We don't actually know the exact date from the API
                self.date_selection_reason = (
                    f"Sentinel-1 search {search_description} (Note: Exact acquisition date unknown - "
                    f"Sentinel-1 has ~12 day revisit time). Data fetched successfully."
                )
                
                print(f"DEBUG: {self.date_selection_reason}")
                return data[-1]
            else:
                self.sar_date = None
                self.date_selection_reason = f"No SAR data available {search_description}. (Sentinel-1 revisit time: ~12 days)"
                print(f"DEBUG: {self.date_selection_reason}")
                return None
        except Exception as e:
            print(f"Error fetching Sentinel-1 data: {e}")
            self.sar_date = None
            self.date_selection_reason = f"Error fetching SAR data: {str(e)}"
            return None


class GEEDataService:
    """Service for fetching JRC permanent water data via Google Earth Engine at 10m resolution."""
    
    def __init__(self):
        self.settings = get_settings()
        self._initialized = False
        
    def _ensure_initialized(self):
        """Initialize Earth Engine if not already done."""
        if self._initialized:
            return
        import ee
        try:
            ee.Initialize(project=self.settings.GEE_PROJECT_ID)
            self._initialized = True
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=self.settings.GEE_PROJECT_ID)
            self._initialized = True
    
    def get_permanent_water(self, lat: float, lon: float) -> Optional[np.ndarray]:
        """
        Fetch JRC permanent water mask at 10m resolution (256x256 pixels).
        Returns numpy array (256, 256) with binary water mask (1=permanent water), or None.
        """
        import ee
        self._ensure_initialized()
        
        radius = self.settings.BUFFER_RADIUS  # 1280m
        target_size = self.settings.IMAGE_SIZE  # 256
        
        # Create geometry
        point = ee.Geometry.Point([lon, lat])
        region = point.buffer(radius).bounds()
        
        # JRC Global Surface Water - transitions band, class 1 = Permanent Water
        jrc = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select('transition')
        water_mask = jrc.eq(1)
        
        # Export at 10m resolution to get 256x256 pixels
        # radius = 1280m, resolution = 10m -> 1280/10 = 128 pixels per side
        # So 256 pixels = 2560m total, radius needed = 1280m ✓
        url = water_mask.getDownloadURL({
            'region': region,
            'scale': 10,  # 10m resolution
            'crs': 'EPSG:4326',
            'format': 'GEO_TIFF'
        })
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                jrc_data = tifffile.imread(io.BytesIO(response.content))
                
                # Center crop to target size (256x256)
                h, w = jrc_data.shape[:2]
                start_x = (w - target_size) // 2
                start_y = (h - target_size) // 2
                
                if start_x >= 0 and start_y >= 0:
                    water_data = jrc_data[start_y:start_y+target_size, start_x:start_x+target_size]
                else:
                    water_data = jrc_data
                
                # Debug output
                unique_vals = np.unique(water_data)
                print(f"DEBUG: JRC water data shape: {water_data.shape}, unique values: {unique_vals}")
                print(f"DEBUG: Water pixels (value=1): {int((water_data == 1).sum())}")
                
                return water_data
            else:
                print(f"Error downloading from GEE: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching JRC water data from GEE: {e}")
            import traceback
            traceback.print_exc()
            return None


class FloodDataService:
    """Combined service for fetching SAR (Sentinel Hub) + JRC (GEE) data."""
    
    def __init__(self):
        self.sentinel = SentinelDataService()
        self.gee = GEEDataService()
        
    def get_flood_data(self, lat: float, lon: float, target_date: Optional[datetime.date] = None, days_back: int = 12) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Fetch Sentinel-1 SAR from Sentinel Hub and JRC permanent water from GEE."""
        s1_data = self.sentinel.get_sentinel1_data(lat, lon, target_date, days_back)
        jrc_data = self.gee.get_permanent_water(lat, lon)
        return s1_data, jrc_data


