# -*- coding: utf-8 -*-
"""
Configuration settings for flood detection module.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class FloodDetectionSettings(BaseSettings):
    """Settings for flood detection services."""
    
    # Sentinel Hub credentials
    SH_CLIENT_ID: str = ""
    SH_CLIENT_SECRET: str = ""
    
    # Google Earth Engine project ID
    GEE_PROJECT_ID: str = ""
    
    # Model paths (relative to backend folder)
    MODEL_PATH: str = "flood_detection/Sen1Floods11_epoch22_iou0.660884_f10.699948.pt"
    
    # Image size settings
    IMAGE_SIZE: int = 256
    BUFFER_RADIUS: int = 1280  # meters
    
    # SAR normalization constants (Sen1Floods11 norms)
    VV_MIN: float = -18.600616455078125
    VV_MAX: float = -4.338556289672852
    VH_MIN: float = -26.719135284423828
    VH_MAX: float = -10.748163223266602
    
    # Normalization mean and std
    NORM_MEAN: tuple = (0.6851, 0.5235)
    NORM_STD: tuple = (0.0820, 0.1102)
    
    # Flood detection threshold (minimum pixels to trigger alert)
    FLOOD_ALERT_THRESHOLD: int = 50
    
    class Config:
        env_file = "flood_detection/.env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> FloodDetectionSettings:
    """Get cached settings instance."""
    return FloodDetectionSettings()
