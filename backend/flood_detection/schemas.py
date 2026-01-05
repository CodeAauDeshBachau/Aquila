from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class FloodDetectionRequest(BaseModel):
    """Request model for flood detection."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    target_date: Optional[date] = Field(None, description="Target date for SAR image. If not provided, uses latest available.")


class FloodDetectionResponse(BaseModel):
    """Response model for flood detection."""
    success: bool
    flood_detected: bool
    message: str
    image: Optional[str] = None  # Base64 encoded RGB PNG image
    sar_date: Optional[str] = None  # Date of SAR image
    date_selection_reason: Optional[str] = None  # Why this date was selected
