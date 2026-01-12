from datetime import datetime
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from numpy import double
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from initDB import init_indexes
from predict2 import get_prediction
from curd import insert_prediction, get_prediction_exact, get_prediction_by_area

API_KEY = "Q43UBJ8WX4NNE7KJGVAKBZ5FU"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_indexes()
    yield


app = FastAPI(lifespan=lifespan)

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # Next.js dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    # initialize()
    return {"status": "OK!"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "query": q}


# @app.post("/predict")
# def predict(item: Event):
#     return {"lat": item.lat, "long": item.long, "date_str": item.date_str}


@app.get("/predict/{lat}/{long}/{date_str}")
async def predict(lat: float, long: float, date_str: str):

    p = await get_prediction_by_area(lat, long, date_str)
    if p:
        return {
            "lat": lat,
            "long": long,
            "date_str": date_str,
            "prediction": p["full_record"],
        }

    pred = get_prediction(lat, long, date_str, API_KEY=API_KEY)
    print(pred)
    if pred:
        await insert_prediction(
            latitude=float(lat),
            longitude=float(long),
            # prediction=float(float(pred["prediction"]["flood_probability"]) * 100),
            # remark=pred["prediction"]["risk_level"],
            date=date_str,
            raw_prediction=pred["prediction"],
            full_record=pred,
        )

        return {"lat": lat, "long": long, "date_str": date_str, "prediction": pred}
    return None


# {"lat":27.701634,"long":84.426599,"date_str":"2024-09-28","prediction":{"flood_probability":0.9762109518051147,"prediction":"Flood","confidence":"97.6%","input_summary":{"location":"(27.701634, 84.426599)","date":"2024-09-28","elevation":"195m","recent_rainfall":"353.7 mm (last 3 days)","soil_memory":"272.4 mm"},"threshold_used":0.5,"risk_level":"Very High","rainfall_analysis":{"last_3_days":"353.7 mm","last_7_days":"378.8 mm","last_15_days":"423.1 mm","soil_memory_30d":"272.4 mm"},"location_context":{"coordinates":"(27.701634, 84.426599)","elevation":"195 m","slope":"2°","distance_to_river":"0 m","topographic_wetness_index":"11.422770885107905"},"forecast":{"next_3_days":"231.1 mm","day_0":"222.6 mm","day_1":"8.5 mm","day_2":"0.0 mm"},"recommendation":"URGENT: High flood risk. Immediate evacuation advised."}}
