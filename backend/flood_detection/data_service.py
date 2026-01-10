import numpy as np
import datetime
import requests
import io
from typing import Optional, Tuple
import tifffile
import cv2
from sentinelhub import (
    SHConfig,
    SentinelHubRequest,
    MimeType,
    CRS,
    BBox,
    DataCollection
)
from skimage.registration import phase_cross_correlation
from scipy.ndimage import shift as nd_shift

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
    
    def get_sentinel1_data(
        self, 
        lat: float, 
        lon: float, 
        target_date: Optional[datetime.date] = None, 
        sar_buffer_days: int = 6
    ) -> Optional[np.ndarray]:
        """
        Fetch Sentinel-1 VV/VH data for a location.
        
        SMART DATE HANDLING:
        - If target_date is None → Uses last sar_buffer_days (default 6) for most recent image
        - If target_date is specified → Searches within ±sar_buffer_days around that date
        
        Parameters:
        -----------
        lat, lon : float
            Coordinates
        target_date : datetime.date or None
            If None: Uses last sar_buffer_days (ORIGINAL BEHAVIOR)
            If specified: Searches within ±sar_buffer_days
        sar_buffer_days : int, optional
            Search window in days (default: 6)
        
        Returns:
        --------
        numpy array (256, 256, 2) with VV and VH bands in dB, or None.
        Sets self.sar_date and self.date_selection_reason for tracking.
        """
        radius = self.settings.BUFFER_RADIUS
        
        # Calculate bounding box
        lat_delta = radius / 111132.954
        lon_delta = radius / (111132.954 * np.cos(np.radians(lat)))
        
        min_lon = np.round((lon - lon_delta) * 10000) / 10000
        min_lat = np.round((lat - lat_delta) * 10000) / 10000
        max_lon = np.round((lon + lon_delta) * 10000) / 10000
        max_lat = np.round((lat + lat_delta) * 10000) / 10000
        
        bbox = BBox(
            bbox=[min_lon, min_lat, max_lon, max_lat],
            crs=CRS.WGS84
        )
        
        # ===== SMART DATE LOGIC =====
        today = datetime.date.today()
        
        if target_date:
            # Don't allow future dates
            if target_date > today:
                self.sar_date = None
                self.date_selection_reason = f"NO SAR for that timeframe (future date not allowed)"
                print(f"DEBUG: {self.date_selection_reason}")
                return None
            
            # Search around target date with configurable buffer (default ±6 days)
            start_date = (target_date - datetime.timedelta(days=sar_buffer_days)).isoformat()
            end_date = (target_date + datetime.timedelta(days=sar_buffer_days + 1)).isoformat()
            search_mode = "nearest"
            search_description = f"within ±{sar_buffer_days} days of {target_date.isoformat()}"
            
            print(f"📅 Mode: DATE SPECIFIED ({target_date})")
            print(f"   Searching ±{sar_buffer_days} days: {start_date} to {end_date}")
            
        else:
            # Default: fetch latest from past sar_buffer_days (Sentinel-1 revisit time)
            end_date = today.isoformat()
            start_date = (today - datetime.timedelta(days=30)).isoformat()
            search_mode = "latest"
            search_description = f"latest from past 30 days"
            
            print("📅 Mode: ORIGINAL (No date specified)")
            print(f"   Using last 30 days: {start_date} to {end_date}")
        
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
          return [
            10 * Math.log(Math.max(sample.VV, 1e-5)) / Math.LN10,
            10 * Math.log(Math.max(sample.VH, 1e-5)) / Math.LN10
          ];
        }
        """
        
        # Use mostRecent for latest, or leave default for nearest
        mosaicking_order = "mostRecent"
        
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


class ESAWorldCoverService:
    """Service for fetching ESA WorldCover permanent water data via Google Earth Engine at 10m resolution."""
    
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
    
    def get_permanent_water_large(self, lat: float, lon: float) -> Optional[np.ndarray]:
        """
        Fetch ESA WorldCover permanent water mask at LARGER size (384x384) for alignment.
        Returns numpy array with binary water mask (1=permanent water), or None.
        """
        import ee
        self._ensure_initialized()
        
        radius = self.settings.BUFFER_RADIUS  # 1280m
        BUFFER_FACTOR = 1.5  # Fetch 50% larger area for alignment
        
        # Create geometry with larger buffer
        point = ee.Geometry.Point([lon, lat])
        radius_large = int(radius * BUFFER_FACTOR)
        region_large = point.buffer(radius_large).bounds()
        
        # ESA WorldCover - class 80 = Permanent Water
        worldcover_collection = ee.ImageCollection("ESA/WorldCover/v200")
        worldcover = worldcover_collection.first().select('Map')
        perm_water_layer = worldcover.eq(80)
        
        url = perm_water_layer.getDownloadURL({
            'region': region_large,
            'scale': 10,  # 10m resolution
            'crs': 'EPSG:4326',
            'format': 'GEO_TIFF'
        })
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                wc_raw = tifffile.imread(io.BytesIO(response.content))
                
                # Handle multi-channel
                if wc_raw.ndim == 3:
                    wc_raw = wc_raw[:, :, 0]
                
                wc_binary = (wc_raw > 0).astype(np.uint8)
                
                # Ensure minimum size
                large_size = int(256 * BUFFER_FACTOR)
                h, w = wc_binary.shape
                
                if h < large_size or w < large_size:
                    pad_h = max(0, large_size - h)
                    pad_w = max(0, large_size - w)
                    wc_binary = np.pad(wc_binary, 
                                      ((pad_h//2, pad_h - pad_h//2), 
                                       (pad_w//2, pad_w - pad_w//2)), 
                                      mode='constant', constant_values=0)
                
                # Center crop to target size
                h, w = wc_binary.shape
                start_y = (h - large_size) // 2
                start_x = (w - large_size) // 2
                perm_water_large = wc_binary[start_y:start_y+large_size, start_x:start_x+large_size]
                
                # Debug output
                print(f"DEBUG: ESA WorldCover shape: {perm_water_large.shape}")
                print(f"DEBUG: Water pixels: {int((perm_water_large > 0).sum())}")
                
                return perm_water_large
            else:
                print(f"Error downloading from GEE: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error fetching ESA WorldCover data from GEE: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def align_and_crop_permanent_water(self, sar_vv: np.ndarray, perm_water_large: np.ndarray) -> np.ndarray:
        """
        Align ESA WorldCover to SAR with special handling for narrow mountain rivers.
        """
        print("\n🔧 ALIGNING AND CROPPING PERMANENT WATER...")
        
        # Detect river type based on water characteristics
        water_pixels = np.sum(perm_water_large > 0)
        total_pixels = perm_water_large.size
        water_percentage = (water_pixels / total_pixels) * 100
        
        # Calculate water shape characteristics
        if water_pixels > 0:
            # Count separate water bodies
            from scipy.ndimage import label
            labeled, num_features = label(perm_water_large > 0)
            
            # Calculate average water body size
            avg_cluster_size = water_pixels / max(num_features, 1)
            
            print(f"   Water coverage: {water_percentage:.2f}%")
            print(f"   Water clusters: {num_features}")
            print(f"   Avg cluster size: {avg_cluster_size:.0f} pixels")
            
            # Determine river type
            is_narrow_river = (water_percentage < 5.0 and avg_cluster_size < 5000)
            is_mountain_river = (num_features <= 3 and water_percentage < 3.0)
            
            if is_mountain_river:
                print(f"   → Detected: NARROW MOUNTAIN RIVER")
                # Use gentler alignment for narrow rivers
                upsample = 5
                orb_nfeatures = 300
                ransac_thresh = 15.0
                lowe_ratio = 0.8  # More permissive
            elif is_narrow_river:
                print(f"   → Detected: NARROW RIVER")
                upsample = 10
                orb_nfeatures = 400
                ransac_thresh = 10.0
                lowe_ratio = 0.75
            else:
                print(f"   → Detected: WIDE/BRAIDED RIVER")
                # Original parameters
                upsample = 20
                orb_nfeatures = 500
                ransac_thresh = 5.0
                lowe_ratio = 0.7
        else:
            print(f"   → No water detected, using default parameters")
            upsample = 20
            orb_nfeatures = 500
            ransac_thresh = 5.0
            lowe_ratio = 0.7
        
        sar_gray = (sar_vv * 255).astype(np.uint8)
        
        print("   Step 1/3: Phase correlation alignment...")
        
        h_large, w_large = perm_water_large.shape
        h_sar, w_sar = sar_vv.shape
        
        center_y = h_large // 2
        center_x = w_large // 2
        half_size = min(h_sar, w_sar) // 2
        
        perm_center = perm_water_large[
            center_y - half_size:center_y + half_size,
            center_x - half_size:center_x + half_size
        ].astype(np.float32)
        
        sar_binary = (sar_vv < 0.35).astype(np.float32)
        
        try:
            shift, error, diffphase = phase_cross_correlation(
                sar_binary, perm_center, 
                upsample_factor=upsample,  # ADAPTIVE
                normalization=None
            )
            
            confidence = 1 - error
            print(f"      Detected shift: Y={shift[0]:.3f}, X={shift[1]:.3f} pixels")
            print(f"      Correlation confidence: {confidence:.4f}")
            
            # For narrow rivers, be more conservative about applying shift
            if is_mountain_river or is_narrow_river:
                if confidence > 0.4 and abs(shift[0]) < 30 and abs(shift[1]) < 30:
                    perm_shifted = nd_shift(
                        perm_water_large.astype(np.float32), 
                        shift, 
                        order=1,  # Linear for narrow rivers (more stable)
                        mode='constant', 
                        cval=0
                    )
                    print(f"      ✓ Conservative shift applied")
                else:
                    print(f"      ⚠️ Shift rejected (confidence {confidence:.3f} or large shift)")
                    perm_shifted = perm_water_large.astype(np.float32)
            else:
                # Wide rivers: use original aggressive shift
                perm_shifted = nd_shift(
                    perm_water_large.astype(np.float32), 
                    shift, 
                    order=3, 
                    mode='constant', 
                    cval=0
                )
            
        except Exception as e:
            print(f"      ⚠️ Phase correlation failed: {e}, using original")
            perm_shifted = perm_water_large.astype(np.float32)
        
        print("   Step 2/3: Feature-based refinement...")
        
        perm_resized = cv2.resize(
            perm_shifted, 
            (w_sar, h_sar), 
            interpolation=cv2.INTER_LINEAR
        )
        perm_resized_gray = (perm_resized * 255).astype(np.uint8)
        
        try:
            orb = cv2.ORB_create(
                nfeatures=orb_nfeatures,  # ADAPTIVE
                scaleFactor=1.2, 
                nlevels=8
            )
            
            kp1, des1 = orb.detectAndCompute(sar_gray, None)
            kp2, des2 = orb.detectAndCompute(perm_resized_gray, None)
            
            if des1 is not None and des2 is not None and len(kp1) > 10 and len(kp2) > 10:
                bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
                matches = bf.knnMatch(des2, des1, k=2)
                
                good_matches = []
                for pair in matches:
                    if len(pair) == 2:
                        m, n = pair
                        if m.distance < lowe_ratio * n.distance:  # ADAPTIVE
                            good_matches.append(m)
                
                print(f"      Found {len(good_matches)} good feature matches")
                
                # For narrow rivers, require fewer matches
                min_matches = 5 if (is_mountain_river or is_narrow_river) else 10
                
                if len(good_matches) >= min_matches:
                    src_pts = np.float32([kp2[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                    dst_pts = np.float32([kp1[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                    
                    scale_y = h_large / h_sar
                    scale_x = w_large / w_sar
                    
                    M, mask = cv2.estimateAffinePartial2D(
                        src_pts * [[scale_x, scale_y]], 
                        dst_pts * [[scale_x, scale_y]],
                        method=cv2.RANSAC,
                        ransacReprojThreshold=ransac_thresh,  # ADAPTIVE
                        confidence=0.99
                    )
                    
                    if M is not None:
                        inliers = np.sum(mask)
                        inlier_ratio = inliers / len(good_matches)
                        
                        # For narrow rivers, require higher inlier ratio
                        min_inlier_ratio = 0.5 if (is_mountain_river or is_narrow_river) else 0.3
                        
                        if inlier_ratio >= min_inlier_ratio:
                            perm_transformed = cv2.warpAffine(
                                perm_shifted.astype(np.float32), 
                                M, 
                                (w_large, h_large),
                                flags=cv2.INTER_LINEAR,
                                borderMode=cv2.BORDER_CONSTANT,
                                borderValue=0
                            )
                            perm_shifted = perm_transformed
                            
                            print(f"      Applied affine transform (inliers: {inliers}/{len(good_matches)}, ratio: {inlier_ratio:.2f})")
                        else:
                            print(f"      ⚠️ Affine rejected (inlier ratio {inlier_ratio:.2f} < {min_inlier_ratio})")
                            
        except Exception as e:
            print(f"      ⚠️ Feature matching failed: {e}")
        
        print("   Step 3/3: Cropping to exact 256x256...")
        
        h_large, w_large = perm_shifted.shape
        center_y = h_large // 2
        center_x = w_large // 2
        
        start_y = center_y - 128
        start_x = center_x - 128
        end_y = start_y + 256
        end_x = start_x + 256
        
        if start_y < 0 or start_x < 0 or end_y > h_large or end_x > w_large:
            print(f"      ⚠️ Cropping out of bounds, adjusting...")
            start_y = max(0, min(start_y, h_large - 256))
            start_x = max(0, min(start_x, w_large - 256))
            end_y = start_y + 256
            end_x = start_x + 256
        
        perm_cropped = perm_shifted[start_y:end_y, start_x:end_x]
        
        if perm_cropped.shape != (256, 256):
            print(f"      ⚠️ Shape mismatch {perm_cropped.shape}, resizing...")
            perm_cropped = cv2.resize(
                perm_cropped, 
                (256, 256), 
                interpolation=cv2.INTER_LINEAR
            )
        
        perm_final = (perm_cropped > 0.5).astype(np.uint8)
        
        # Morphological closing to fill small gaps
        kernel = np.ones((3, 3), np.uint8)
        perm_final = cv2.morphologyEx(perm_final, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        print(f"   ✓ ALIGNMENT & CROPPING COMPLETE")
        print(f"      Final shape: {perm_final.shape}")
        
        # Calculate alignment IoU
        sar_water_mask = (sar_binary > 0.5).astype(np.uint8)
        intersection = np.sum(sar_water_mask & perm_final)
        union = np.sum(sar_water_mask | perm_final)
        iou = intersection / (union + 1e-6)
        print(f"      Alignment IoU: {iou:.3f}")
        
        if iou < 0.3:
            print(f"      ⚠️ LOW ALIGNMENT QUALITY - Model will use SAR-based water detection")
        
        return perm_final


class FloodDataService:
    """Combined service for fetching SAR (Sentinel Hub) + ESA WorldCover (GEE) data."""
    
    def __init__(self):
        self.sentinel = SentinelDataService()
        self.esa = ESAWorldCoverService()
    
    def get_flood_data(
        self, 
        lat: float, 
        lon: float, 
        target_date: Optional[datetime.date] = None, 
        sar_buffer_days: int = 6
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Fetch Sentinel-1 SAR from Sentinel Hub and ESA WorldCover permanent water from GEE.
        
        Parameters:
        -----------
        lat, lon : float
            Coordinates
        target_date : datetime.date or None
            If None: Uses last sar_buffer_days for most recent image
            If specified: Searches within ±sar_buffer_days around that date
        sar_buffer_days : int, optional
            Search window in days (default: 6)
        
        Returns:
        --------
        Tuple of (SAR data (256x256x2), ESA WorldCover large (384x384+))
        """
        s1_data = self.sentinel.get_sentinel1_data(lat, lon, target_date, sar_buffer_days)
        esa_data_large = self.esa.get_permanent_water_large(lat, lon)
        return s1_data, esa_data_large
