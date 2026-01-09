import numpy as np
import torch
from torchvision import transforms
from typing import Optional, Dict
import base64
import io
from PIL import Image
from .config import get_settings


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
    
    def predict(
        self, 
        s1_image: np.ndarray, 
        esa_water_large: Optional[np.ndarray] = None,
        esa_service = None
    ) -> tuple:
        """
        Run flood detection and return (flood_detected, images_dict).
        
        Args:
            s1_image: SAR image (H, W, 2) with VV/VH bands
            esa_water_large: ESA WorldCover large water mask (384x384+) for alignment
            esa_service: ESAWorldCoverService instance for alignment
            
        Returns:
            tuple: (flood_detected: bool, images: Dict[str, str])
                   where images contains base64 encoded PNGs:
                   - 'sar': Pure SAR grayscale
                   - 'permanent_water': Permanent water (blue) on SAR
                   - 'model_water': Model water detection (red) on SAR
                   - 'classification': Classification map on SAR
                   - 'flood_only': New flood only (red) on SAR
        """
        self._load_model()
        
        # Preprocess SAR
        vv = torch.from_numpy(s1_image[:, :, 0]).float()
        vh = torch.from_numpy(s1_image[:, :, 1]).float()
        
        print(f"DEBUG: Raw SAR ranges - VV: [{vv.min():.2f}, {vv.max():.2f}], VH: [{vh.min():.2f}, {vh.max():.2f}]")
        
        # Normalize to expected range if outside bounds
        # If SAR values are in linear scale (0-1), convert to dB range
        if vv.max() <= 1.0:
            vv = torch.log10(torch.clamp(vv, 1e-6, 1.0)) * 10
            vh = torch.log10(torch.clamp(vh, 1e-6, 1.0)) * 10
            print(f"DEBUG: Converted to dB - VV: [{vv.min():.2f}, {vv.max():.2f}], VH: [{vh.min():.2f}, {vh.max():.2f}]")
        
        vv = torch.clamp(vv, self.settings.VV_MIN, self.settings.VV_MAX)
        vh = torch.clamp(vh, self.settings.VH_MIN, self.settings.VH_MAX)
        
        vv_norm = (vv - self.settings.VV_MIN) / (self.settings.VV_MAX - self.settings.VV_MIN + 1e-6)
        vh_norm = (vh - self.settings.VH_MIN) / (self.settings.VH_MAX - self.settings.VH_MIN + 1e-6)
        
        img_tensor = torch.stack([vv_norm, vh_norm], dim=0)
        img_tensor = transforms.Normalize(list(self.settings.NORM_MEAN), list(self.settings.NORM_STD))(img_tensor)
        img_input = img_tensor.unsqueeze(0).to(self.device)
        
        # Inference
        with torch.no_grad():
            output = self.model(img_input)
            prediction = torch.argmax(output, dim=1).squeeze().cpu().numpy()
        
        # Get permanent water mask using ESA WorldCover with alignment
        if esa_water_large is not None and esa_service is not None:
            # Use alignment from Colab
            perm_water = esa_service.align_and_crop_permanent_water(
                vv_norm.numpy(), 
                esa_water_large
            )
            
            # Correct model prediction with aligned permanent water
            prediction_corrected = prediction.copy()
            prediction_corrected[perm_water == 1] = 1
            prediction = prediction_corrected
            
            perm_water = (perm_water > 0).astype(bool)
        else:
            # Fallback to model class 1
            perm_water = (prediction == 1)
        
        # Model water = classes 1 (water) + 2 (flood) before correction
        model_water_mask = (prediction == 1) | (prediction == 2)
        
        # Flood = model class 2, excluding permanent water
        flood_mask = (prediction == 2) & (~perm_water)
        flood_pixels = int(flood_mask.sum())
        water_pixels = int(perm_water.sum())
        
        # Determine if flood detected based on pixel ratio
        flood_detected = self._is_flood_detected(flood_pixels, water_pixels)
        
        # Analyze flood extent
        self.analyze_flood_extent(flood_pixels, water_pixels)
        
        # Generate all 5 images like Colab
        images = self._create_five_panel_images(
            vv_norm.numpy(), 
            perm_water, 
            model_water_mask,
            prediction, 
            flood_mask
        )
        
        return flood_detected, images
    
    def _is_flood_detected(self, flood_pixels: int, water_pixels: int) -> bool:
        """
        Determine if flood is detected based on pixel ratio.
        Flood is detected if red pixels are 20%+ of blue water pixels.
        """
        if water_pixels == 0:
            return flood_pixels > self.settings.FLOOD_ALERT_THRESHOLD
        
        # Calculate ratio
        ratio = (flood_pixels / water_pixels) * 100
        
        # Flood detected if ratio >= 20%
        return ratio >= 20
    
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
        prediction: np.ndarray, 
        flood_mask: np.ndarray
    ) -> Dict[str, str]:
        """
        Create 5 separate images matching Colab output:
        A: Pure SAR (grayscale)
        B: Permanent Water (blue) overlaid on SAR
        C: Model Water Detection (red) overlaid on SAR
        D: Classification Map (blue=water, red=flood) overlaid on SAR
        E: New Flood Only (red) overlaid on SAR
        
        Returns dict with base64 encoded PNG images.
        """
        # Apply contrast stretching to SAR data for better visibility
        vv_min = np.percentile(vv_norm, 2)  # Use 2nd percentile to handle outliers
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
        # Blue overlay for permanent water
        img_b[perm_water] = [0, 100, 200]  # Blue (R, G, B)
        images['permanent_water'] = self._numpy_to_base64(img_b)
        
        # ============ IMAGE C: Model Water Detection (RED) on SAR ============
        img_c = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        # Red overlay for model water detection
        img_c[model_water] = [200, 50, 50]  # Red (R, G, B)
        images['model_water'] = self._numpy_to_base64(img_c)
        
        # ============ IMAGE D: Classification Map on SAR ============
        img_d = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        # Blue for permanent water (class 1)
        img_d[prediction == 1] = [0, 100, 200]  # Blue
        # Red for flood (class 2)
        img_d[prediction == 2] = [200, 50, 50]  # Red
        images['classification'] = self._numpy_to_base64(img_d)
        
        # ============ IMAGE E: New Flood Only (RED) on SAR ============
        img_e = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2).copy()
        # Red overlay for new flood only
        img_e[flood_mask] = [200, 50, 50]  # Red (R, G, B)
        images['flood_only'] = self._numpy_to_base64(img_e)
        
        return images
    
    def _numpy_to_base64(self, img_array: np.ndarray) -> str:
        """Convert numpy array to base64 encoded PNG string."""
        pil_image = Image.fromarray(img_array.astype(np.uint8), mode='RGB')
        buf = io.BytesIO()
        pil_image.save(buf, format='PNG')
        buf.seek(0)
        return base64.b64encode(buf.read()).decode('utf-8')
