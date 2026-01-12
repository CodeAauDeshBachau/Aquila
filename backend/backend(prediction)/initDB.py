from database import prediction_collection


async def init_indexes():
    # Geospatial index (REQUIRED)

    print("DB:", prediction_collection.database.name)
    print("Collection:", prediction_collection.name)
    print("Client:", prediction_collection.database.client)

    await prediction_collection.create_index(
        [("location", "2dsphere")], name="location_2dsphere"
    )

    # Date index
    await prediction_collection.create_index([("date", 1)], name="date_1")
