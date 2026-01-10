import numpy as np
import torch
from torchvision import transforms
from typing import Optional, Dict
import base64
import io
from PIL import Image
from .config import get_settings
from scipy import ndimage


class FloodModelService:
    """Service for flood detection model inference."""
    
    def __init__(self):
        self.settings = get_settings()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self._model_loaded = False
        
    def _load_model(self):
        """Load the model if not already loaded."""
        if self._model_loaded:
            return
            
        import segmentation_models_pytorch as smp
        
        self.model = smp.UnetPlusPlus(
            encoder_name="efficientnet-b4",
            encoder_weights=None,
            in_channels=2,
            classes=3,
        )
        self.model = self.model.to(self.device)
        
        ckpt = torch.load(self.settings.MODEL_PATH, map_location=self.device)
        state_dict = ckpt.get("model_state_dict", ckpt) if isinstance(ckpt, dict) else ckpt
        self.model.load_state_dict(state_dict, strict=False)
        self.model.eval()
        self._model_loaded = True
    
    def _filter_small_flood_patches(self, flood_mask: np.ndarray, min_patch_size: int = 100) -> np.ndarray:
        """
        Filter out small isolated flood patches that are likely shadows.
        
        Args:
            flood_mask: Boolean array of detected flood pixels
            min_patch_size: Minimum number of connected pixels to be considered valid flood
            
        Returns:
            Filtered flood mask with small patches removed
        """
        # Label connected components
        labeled_array, num_features = ndimage.label(flood_mask)
        
        # Count pixels in each component
        component_sizes = np.bincount(labeled_array.ravel())
        
        # Keep only components larger than threshold
        mask_sizes = component_sizes > min_patch_size
        mask_sizes[0] = False  # Background is always 0
        
        # Create filtered mask
        filtered_mask = mask_sizes[labeled_array]
        
        num_removed = num_features - (mask_sizes.sum() - 1)  # -1 for background
        print(f"DEBUG: Filtered out {num_removed} small patches (< {min_patch_size} pixels)")
        print(f"DEBUG: Remaining flood patches: {mask_sizes.sum() - 1}")
        
        return filtered_mask
    
    def predict(
        self,
        s1_image: np.ndarray,
        esa_water_large: Optional[np.ndarray] = None,
        esa_service = None
    ) -> tuple:
        """Run flood detection and return (flood_detected, images_dict)."""
        self._load_model()

        # Preprocess SAR
        vv = torch.from_numpy(s1_image[:, :, 0]).float()
        vh = torch.from_numpy(s1_image[:, :, 1]).float()
        print(f"DEBUG: Raw SAR ranges - VV: [{vv.min():.2f}, {vv.max():.2f}], VH: [{vh.min():.2f}, {vh.max():.2f}]")

        # Normalize to expected range
        if vv.max() <= 1.0:
            vv = torch.log10(torch.clamp(vv, 1e-6, 1.0)) * 10
            vh = torch.log10(torch.clamp(vh, 1e-6, 1.0)) * 10
            print(f"DEBUG: Converted to dB - VV: [{vv.min():.2f}, {vv.max():.2f}], VH: [{vh.min():.2f}, {vh.max():.2f}]")

        # Clamp to configured dB range
        vv = torch.clamp(vv, self.settings.VV_MIN, self.settings.VV_MAX)
        vh = torch.clamp(vh, self.settings.VH_MIN, self.settings.VH_MAX)

        # Normalise to 0–1
        vv_norm = (vv - self.settings.VV_MIN) / (self.settings.VV_MAX - self.settings.VV_MIN + 1e-6)
        vh_norm = (vh - self.settings.VH_MIN) / (self.settings.VH_MAX - self.settings.VH_MIN + 1e-6)

        img_tensor = torch.stack([vv_norm, vh_norm], dim=0)
        img_tensor = transforms.Normalize(list(self.settings.NORM_MEAN), list(self.settings.NORM_STD))(img_tensor)
        img_input = img_tensor.unsqueeze(0).to(self.device)

        # Inference - GET MODEL'S ACTUAL PREDICTION
        with torch.no_grad():
            output = self.model(img_input)
            prediction = torch.argmax(output, dim=1).squeeze().cpu().numpy()

        # ========== SHADOW FILTERING - DISABLED FOR TESTING ==========
        print("   Applying shadow filtering...")
        vv_np = vv.cpu().numpy()
        vh_np = vh.cpu().numpy()
        
        # 1) Extremely low VV = likely shadow
        shadow_mask = (vv_np < -22.0).astype(bool)
        
        # 2) Very low VH = likely shadow
        vh_too_low = (vh_np < -28.0).astype(bool)
        shadow_mask = shadow_mask | vh_too_low
        
        # 3) Low texture variance = uniform dark areas (shadow)
        from scipy.ndimage import generic_filter
        def local_std(x):
            return np.std(x)
        
        vv_variance = generic_filter(vv_np, local_std, size=5)
        low_variance_mask = (vv_variance < 1.0).astype(bool)
        shadow_mask = shadow_mask & low_variance_mask
        
        # Force shadow pixels to background
        prediction[shadow_mask] = 0
        print(f"   DEBUG: Filtered {shadow_mask.sum()} shadow pixels")
        # ================================================================

        # Get permanent water mask from ESA WorldCover
        if esa_water_large is not None and esa_service is not None:
            perm_water = esa_service.align_and_crop_permanent_water(
                vv_norm.numpy(),
                esa_water_large
            )
            perm_water = (perm_water > 0).astype(bool)
        else:
            # Fallback: Use model's class 1 as permanent water
            perm_water = (prediction == 1)

        # --- Restrict model water to a relaxed band around ESA perm-water (ACTIVE) ---
        from scipy.ndimage import distance_transform_edt

        if perm_water.any():
            # distance in pixels from nearest ESA perm-water pixel
            dist = distance_transform_edt(~perm_water)

            # max distance where model is allowed to call "water" (200 meters at 10m/pixel)
            max_water_dist = 20.0

            # water for visualization and analysis: only within ESA buffer
            model_water_mask = ((prediction == 1) | (prediction == 2)) & (dist <= max_water_dist)

            # tighten prediction: far-away water/flood -> background
            prediction_tight = prediction.copy()
            prediction_tight[(prediction_tight != 0) & (dist > max_water_dist)] = 0
        else:
            model_water_mask = (prediction == 1) | (prediction == 2)
            prediction_tight = prediction.copy()
        # ----------------------------------------------------------------------------

        # Create CORRECTED prediction for classification image (overlay ESA)
        prediction_corrected = prediction_tight.copy()
        prediction_corrected[perm_water] = 1  # ESA permanent water wins

        # Flood detection logic:
        # Red areas (class 2) from TIGHTENED prediction that are NOT ESA perm-water
        flood_mask_raw = (prediction_tight == 2) & (~perm_water)

        # Filter out small patches - DISABLED FOR TESTING
        # flood_mask = self._filter_small_flood_patches(flood_mask_raw, min_patch_size=200)
        flood_mask = flood_mask_raw  # Use raw mask without filtering

        flood_pixels = int(flood_mask.sum())
        water_pixels = int(perm_water.sum())

        # Determine if flood detected
        flood_detected = self._is_flood_detected(flood_pixels, water_pixels)

        # Analyze flood extent
        self.analyze_flood_extent(flood_pixels, water_pixels)

        # Generate all 5 images
        images = self._create_five_panel_images(
            vv_norm.numpy(),
            perm_water,
            model_water_mask,        # constrained water mask for Image C
            prediction_tight,        # "raw" (but slightly tightened) prediction for Image C/D
            prediction_corrected,    # ESA-corrected for Image D
            flood_mask
        )

        return flood_detected, images


    
    def _is_flood_detected(self, flood_pixels: int, water_pixels: int, min_water_pixels: int = 100) -> bool:
        """
        Determine if flood is detected based on:
        1. Presence of permanent water source (water_pixels > threshold)
        2. Red flood pixels are 20%+ of blue water pixels
        3. Small isolated patches already filtered out
        
        Args:
            flood_pixels: Number of flood pixels after filtering
            water_pixels: Number of permanent water pixels
            min_water_pixels: Minimum permanent water pixels required
            
        Returns:
            True if flood detected, False otherwise
        """
        # Check 1: Must have permanent water source
        if water_pixels < min_water_pixels:
            print(f"DEBUG: No significant permanent water source ({water_pixels} < {min_water_pixels}). No flood alert.")
            return False
        
        # Check 2: Must have flood pixels
        if flood_pixels == 0:
            print(f"DEBUG: No flood pixels detected after filtering.")
            return False
        
        # Check 3: Calculate ratio
        ratio = (flood_pixels / water_pixels) * 100
        
        # Flood detected if ratio >= 20%
        is_flood = ratio >= 20.0
        
        print(f"DEBUG: Flood-to-water ratio: {ratio:.2f}% (threshold: 20%)")
        print(f"DEBUG: Flood detected: {is_flood}")
        
        return is_flood
    
    def analyze_flood_extent(self, flood_pixels: int, water_pixels: int, total_pixels: int = 256*256) -> dict:
        """
        Analyze flood extent by comparing flooded areas to permanent water areas.
        
        Returns dict with:
            - water_pixels: count of permanent water pixels
            - flood_pixels: count of flooded pixels
            - water_percentage: % of image that is permanent water
            - flood_percentage: % of image that is flooded
            - flood_to_water_ratio: flooded pixels as % of water pixels
            - flood_severity: classification (None, Low, Moderate, High, Extreme)
            - flood_detected: bool indicating if flood is significant
        """
        water_pct = (water_pixels / total_pixels) * 100
        flood_pct = (flood_pixels / total_pixels) * 100
        flood_to_water_ratio = (flood_pixels / water_pixels * 100) if water_pixels > 0 else 0
        
        # Classify flood severity
        if flood_pixels == 0 or water_pixels == 0:
            severity = "None"
        elif flood_to_water_ratio < 5:
            severity = "Low"
        elif flood_to_water_ratio < 20:
            severity = "Moderate"
        elif flood_to_water_ratio < 50:
            severity = "High"
        else:
            severity = "Extreme"
        
        flood_detected = self._is_flood_detected(flood_pixels, water_pixels)
        
        analysis = {
            "permanent_water_pixels": int(water_pixels),
            "flooded_pixels": int(flood_pixels),
            "permanent_water_percentage": round(water_pct, 2),
            "flooded_percentage": round(flood_pct, 2),
            "flood_to_water_ratio": round(flood_to_water_ratio, 2),
            "flood_severity": severity,
            "flood_detected": flood_detected
        }
        
        # Print detailed analysis
        print("\n" + "="*60)
        print("FLOOD ANALYSIS REPORT")
        print("="*60)
        print(f"Permanent Water Pixels: {water_pixels:,} ({water_pct:.2f}% of image)")
        print(f"Flooded Pixels: {flood_pixels:,} ({flood_pct:.2f}% of image)")
        print(f"Flood-to-Water Ratio: {flood_to_water_ratio:.2f}%")
        print(f"Flood Severity: {severity}")
        print(f"Flood Detected: {flood_detected}")
        print("="*60 + "\n")
        
        return analysis
    
    def _create_five_panel_images(
        self, 
        vv_norm: np.ndarray, 
        perm_water: np.ndarray,
        model_water: np.ndarray,
        prediction_raw: np.ndarray,      # Model's original prediction
        prediction_corrected: np.ndarray, # ESA-corrected prediction
        flood_mask: np.ndarray
    ) -> Dict[str, str]:
        """
        Create 5 separate images matching Colab output:
        A: Pure SAR (grayscale)
        B: Permanent Water (blue) overlaid on SAR
        C: Model Water Detection (red) overlaid on SAR - uses RAW model prediction
        D: Classification Map (blue=water, red=flood) overlaid on SAR - uses CORRECTED prediction
        E: New Flood Only (red) overlaid on SAR
        
        Returns dict with base64 encoded PNG images.
        """
        # Apply contrast stretching to SAR data for better visibility
        vv_min = np.percentile(vv_norm, 2)
        vv_max = np.percentile(vv_norm, 98)
        
        if vv_max > vv_min:
            sar_stretched = (vv_norm - vv_min) / (vv_max - vv_min + 1e-6)
        else:
            sar_stretched = vv_norm
        
        # Clamp to 0-1 range and convert to 0-255
        sar_intensity = (np.clip(sar_stretched, 0, 1) * 255).astype(np.uint8)
        
        print(f"DEBUG: SAR intensity range after stretch: [{sar_intensity.min()}, {sar_intensity.max()}]")
        print(f"DEBUG: Flood pixels: {flood_mask.sum()}, Water pixels: {perm_water.sum()}")
        
        images = {}
        
        # ============ IMAGE A: Pure SAR ============
        img_a = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2)
        images['sar'] = self._numpy_to_base64(img_a)
        
        # ============ IMAGE B: Permanent Water (BLUE) on SAR ============
        img_b = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        img_b[perm_water] = [0, 100, 200]  # Blue
        images['permanent_water'] = self._numpy_to_base64(img_b)
        
        # ============ IMAGE C: Model Water Detection (RED) on SAR ============
        img_c = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        img_c[model_water] = [200, 50, 50]  # Red - shows what MODEL detected
        images['model_water'] = self._numpy_to_base64(img_c)
        
        # ============ IMAGE D: Classification Map on SAR (CORRECTED) ============
        img_d = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        # Use CORRECTED prediction - ESA permanent water overlaid
        img_d[prediction_corrected == 1] = [0, 100, 200]  # Blue - permanent water
        img_d[prediction_corrected == 2] = [200, 50, 50]  # Red - flood
        images['classification'] = self._numpy_to_base64(img_d)
        
        # ============ IMAGE E: New Flood Only (RED) on SAR ============
        img_e = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        img_e[flood_mask] = [200, 50, 50]  # Red
        images['flood_only'] = self._numpy_to_base64(img_e)
        
        return images

    
    def _numpy_to_base64(self, img_array: np.ndarray) -> str:
        """Convert numpy array to base64 encoded PNG string."""
        pil_image = Image.fromarray(img_array.astype(np.uint8), mode='RGB')
        buf = io.BytesIO()
        pil_image.save(buf, format='PNG')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
