from datetime import datetime, timedelta, timezone, timezone
from pymongo.errors import DuplicateKeyError
from database import prediction_collection

from pymongo.errors import DuplicateKeyError
from database import prediction_collection


async def insert_prediction(
    latitude: float,
    longitude: float,
    # prediction: float,
    # remark: str,
    date: str,
    raw_prediction: dict,
    full_record: dict,
):
    date = datetime.strptime(date, "%Y-%m-%d")
    latitude = round(latitude, 5)
    longitude = round(longitude, 5)
    document = {
        "location": {"type": "Point", "coordinates": [longitude, latitude]},
        # "prediction": prediction,
        # "remark": remark,
        "date": datetime(date.year, date.month, date.day),
        "created_at": datetime.now(timezone.utc),
        "raw_prediction": raw_prediction,
        "full_record": full_record,
    }

    try:
        await prediction_collection.insert_one(document)
        return {"status": "inserted"}
    except DuplicateKeyError:
        return {"status": "already_exists"}


from datetime import datetime


async def get_prediction_exact(latitude: float, longitude: float, date: datetime):
    query_date = datetime(date.year, date.month, date.day)
    latitude = round(latitude, 5)
    longitude = round(longitude, 5)

    result = await prediction_collection.find_one(
        {
            "location": {"type": "Point", "coordinates": [longitude, latitude]},
            "date": query_date,
        }
    )

    if result:
        return result
    return False


async def get_prediction_by_area(
    latitude: float,
    longitude: float,
    date: str,
    radius_km: float = 3,
):
    date_obj = datetime.strptime(date, "%Y-%m-%d")
    start_date = datetime(date_obj.year, date_obj.month, date_obj.day)
    end_date = start_date + timedelta(days=1)

    latitude = round(latitude, 5)
    longitude = round(longitude, 5)

    cursor = prediction_collection.find(
        {
            "location": {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude],
                    },
                    "$maxDistance": radius_km * 1000,
                }
            },
            "date": {"$gte": start_date, "$lt": end_date},
        }
    ).limit(1)

    result = await cursor.to_list(length=1)

    if not result:
        return False

    result[0]["_id"] = str(result[0]["_id"]) if result else None
    return result[0]
