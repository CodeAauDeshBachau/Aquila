from pydantic import BaseModel, EmailStr
from typing import Optional


class PredictionResult(BaseModel):
    lat: float
    long: float
    date_str: str
    prediction: float
    remarks: Optional[str] = None
