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
    try:
        # Fetch SAR + JRC data
        data_service = get_data_service()
        s1_data, jrc_data = data_service.get_flood_data(
            request.latitude, request.longitude, request.target_date
        )
        
        if s1_data is None:
            return FloodDetectionResponse(
                success=False,
                flood_detected=False,
                message="No SAR data available for this location",
                sar_date=data_service.sentinel.sar_date,
                date_selection_reason=data_service.sentinel.date_selection_reason
            )
        
        # Run model with JRC data for accurate permanent water overlay
        flood_detected, image_b64 = get_model_service().predict(s1_data, jrc_data)
        
        return FloodDetectionResponse(
            success=True,
            flood_detected=flood_detected,
            message="Flood detected!" if flood_detected else "No flood detected",
            image=image_b64,
            sar_date=data_service.sentinel.sar_date,
            date_selection_reason=data_service.sentinel.date_selection_reason
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/detect/{lat}/{lon}", response_model=FloodDetectionResponse)
async def detect_flood_get(lat: float, lon: float, target_date: date = None):
    return await detect_flood(FloodDetectionRequest(latitude=lat, longitude=lon, target_date=target_date))


