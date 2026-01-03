from fastapi import FastAPI
from numpy import double
from pydantic import BaseModel

from predict2 import get_prediction

API_KEY = "BDH7AMTHKFDJWJTU8QGGEV877"


app = FastAPI()


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
def predict(lat: float, long: float, date_str: str):

    prediction = get_prediction(lat, long, date_str, API_KEY=API_KEY)
    return {"lat": lat, "long": long, "date_str": date_str, "prediction": prediction}
    return None
