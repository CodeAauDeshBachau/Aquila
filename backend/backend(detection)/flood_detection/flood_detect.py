from fastapi import APIRouter, HTTPException
from datetime import date
from .schemas import FloodDetectionRequest, FloodDetectionResponse
from .data_service import FloodDataService
from .model_service import FloodModelService

router = APIRouter(prefix="/flood", tags=["Flood Detection"])

# Lazy-loaded services
_data_service = None
_model_service = None


def get_data_service():
    global _data_service
    if _data_service is None:
        _data_service = FloodDataService()
    return _data_service


def get_model_service():
    global _model_service
    if _model_service is None:
        _model_service = FloodModelService()
    return _model_service


@router.post("/detect", response_model=FloodDetectionResponse)
async def detect_flood(request: FloodDetectionRequest):
    """
    Detect floods at a specific location using ESA WorldCover with alignment.
    Returns 5 separate images like Colab notebook.
    """
    try:
        # Fetch SAR + ESA WorldCover data
        data_service = get_data_service()
        s1_data, esa_data_large = data_service.get_flood_data(
            request.latitude, 
            request.longitude, 
            request.target_date,
            request.sar_buffer_days
        )
        
        if s1_data is None:
            return FloodDetectionResponse(
                success=False,
                flood_detected=False,
                message="No SAR data available for this location and time range",
                sar_date=data_service.sentinel.sar_date,
                date_selection_reason=data_service.sentinel.date_selection_reason
            )
        
        # Run model with ESA WorldCover data and alignment service
        flood_detected, images = get_model_service().predict(
            s1_data, 
            esa_data_large,
            data_service.esa  # Pass ESA service for alignment
        )
        
        return FloodDetectionResponse(
            success=True,
            flood_detected=flood_detected,
            message="Flood detected!" if flood_detected else "No flood detected",
            images=images,  # Now returns dict with 5 images
            image=images.get('classification'),  # Backward compatibility
            sar_date=data_service.sentinel.sar_date,
            date_selection_reason=data_service.sentinel.date_selection_reason
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect/{lat}/{lon}", response_model=FloodDetectionResponse)
async def detect_flood_get(
    lat: float, 
    lon: float, 
    target_date: date = None, 
    sar_buffer_days: int = 6
):
    """Detect floods at a specific location (GET endpoint)."""
    return await detect_flood(
        FloodDetectionRequest(
            latitude=lat, 
            longitude=lon, 
            target_date=target_date,
            sar_buffer_days=sar_buffer_days
        )
    )
