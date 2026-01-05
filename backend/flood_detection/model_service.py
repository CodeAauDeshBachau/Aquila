import numpy as np
import torch
from torchvision import transforms
from typing import Optional
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
    
    def predict(self, s1_image: np.ndarray, jrc_water: Optional[np.ndarray] = None) -> tuple:
        """
        Run flood detection and return (flood_detected, pixel_intensity_array).
        
        Args:
            s1_image: SAR image (H, W, 2) with VV/VH bands
            jrc_water: Optional JRC permanent water mask (H, W)
        """
        self._load_model()
        
        # Preprocess
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
        
        # Get permanent water mask (prefer JRC, fallback to model class 1)
        if jrc_water is not None:
            perm_water = (jrc_water[:, :, 0] if jrc_water.ndim == 3 else jrc_water) > 0
        else:
            perm_water = (prediction == 1)
        
        # Flood = model class 2, excluding permanent water
        flood_mask = (prediction == 2) & (~perm_water)
        flood_pixels = int(flood_mask.sum())
        water_pixels = int(perm_water.sum())
        
        # Determine if flood detected based on pixel ratio
        flood_detected = self._is_flood_detected(flood_pixels, water_pixels)
        
        # Analyze flood extent
        self.analyze_flood_extent(flood_pixels, water_pixels)
        
        # Generate colored overlay image
        pixel_intensity = self._create_grayscale_image(vv_norm.numpy(), flood_mask, perm_water)
        
        return flood_detected, pixel_intensity
    
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
    
    def _create_grayscale_image(self, vv_norm: np.ndarray, flood_mask: np.ndarray, perm_water: np.ndarray) -> str:
        """
        Create RGB image with colored overlays on SAR background.
        - SAR background as grayscale
        - Red overlay for detected floods
        - Blue overlay for permanent water (on top)
        
        Returns base64 encoded PNG image string.
        """
        # Apply contrast stretching to SAR data for better visibility
        # Normalize to 0-1 range based on actual min/max in the data
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
        
        # Create RGB image starting with grayscale SAR
        height, width = vv_norm.shape
        rgb_image = np.stack([sar_intensity, sar_intensity, sar_intensity], axis=2)
        
        # Add red overlay for flood areas
        rgb_image[flood_mask] = [200, 50, 50]  # Red color (R, G, B)
        
        # Add blue overlay for permanent water ON TOP (drawn last so it's visible)
        rgb_image[perm_water] = [0, 100, 200]  # Blue color (R, G, B)
        
        # Convert to PIL Image (RGB mode)
        pil_image = Image.fromarray(rgb_image.astype(np.uint8), mode='RGB')
        
        # Save to bytes buffer as PNG
        buf = io.BytesIO()
        pil_image.save(buf, format='PNG')
        buf.seek(0)
        
        # Encode to base64
        return base64.b64encode(buf.read()).decode('utf-8')