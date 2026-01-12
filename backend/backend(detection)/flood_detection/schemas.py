from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import date


class FloodDetectionRequest(BaseModel):
    """Request model for flood detection."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")
    target_date: Optional[date] = Field(
        None, 
        description="Target date for SAR image. If not provided, uses latest available from past 6 days."
    )
    sar_buffer_days: int = Field(
        6, 
        ge=1, 
        le=30,
        description="Search window around target_date (±N days). Only used when target_date is specified. Default: 6 days."
    )


class FloodDetectionResponse(BaseModel):
    """Response model for flood detection."""
    success: bool
    flood_detected: bool
    message: str
    images: Optional[Dict[str, str]] = Field(
        None,
        description="Dictionary of base64 encoded PNG images: 'sar', 'permanent_water', 'model_water', 'classification', 'flood_only'"
    )
    sar_date: Optional[str] = None  # Date of SAR image
    date_selection_reason: Optional[str] = None  # Why this date was selected
    
    # Legacy field for backward compatibility (deprecated)
    image: Optional[str] = Field(
        None, 
        description="DEPRECATED: Use 'images' dict instead. This returns the classification image for backward compatibility."
    )
