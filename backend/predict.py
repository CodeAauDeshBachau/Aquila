import ee
import math
import pandas as pd
import numpy as np
import joblib
import lightgbm as lgb

# Initialize Earth Engine
# ee.Initialize()
# ee.Reset()
# authenticate for the first time, then authentication code should be commented
ee.Authenticate()
ee.Initialize(project="aquila-478516")
lat = 27.806678
lon = 84.905390

# 2.535036, 45.244423
# 34.250391, 65.993110


#
# 28.908200, 82.278749
# 27.806678, 84.905390
date_str = "2024-09-29"
API_KEY = "BDH7AMTHKFDJWJTU8QGGEV877"
# BDH7AMTHKFDJWJTU8QGGEV877
# Q43UBJ8WX4NNE7KJGVAKBZ5FU


def get_point_flood_features(lat, lon, date_str):
    """
    Extracts V10 features for a specific lat/long and date.

    Args:
        lat (float): Latitude
        lon (float): Longitude
        date_str (str): Date in 'YYYY-MM-DD'
    """
    point = ee.Geometry.Point([lon, lat])
    ee_date = ee.Date(date_str)

    # 1. STATIC DATASETS
    srtm = ee.Image("USGS/SRTMGL1_003")
    flowAcc = ee.Image("WWF/HydroSHEDS/15ACC")
    rivers = ee.FeatureCollection("WWF/HydroSHEDS/v1/FreeFlowingRivers")
    landcover = ee.ImageCollection("MODIS/006/MCD12Q1").first().select("LC_Type1")

    # 2. CALCULATED STATIC FEATURES
    elevation = srtm.rename("elevation")
    slope = ee.Algorithms.Terrain(srtm).select("slope")

    # TWI Calculation (V10 Cleaned Version)
    cellArea = ee.Image.pixelArea()
    cellWidth = cellArea.sqrt()
    slopeRad = slope.multiply(math.pi).divide(180)
    slopeTan = slopeRad.tan().abs().max(0.001)
    flowAccArea = flowAcc.multiply(cellArea)

    twi = flowAccArea.divide(slopeTan).log10().rename("TWI").clamp(0, 20)

    # Distance to River (V10 logic)
    riverMask = ee.Image(0).paint(rivers, 1)
    distToRiver = (
        riverMask.fastDistanceTransform()
        .sqrt()
        .multiply(cellWidth)
        .divide(1000)
        .rename("dist_to_river")
    )

    static_stack = ee.Image.cat(
        [
            elevation,
            slope.rename("slope"),
            twi,
            distToRiver,
            landcover.rename("landcover"),
        ]
    )

    # 3. TEMPORAL & FLOOD EVENT DATA
    # Lookup the Global Flood Database for this specific point/date
    gfd = (
        ee.ImageCollection("GLOBAL_FLOOD_DB/MODIS_EVENTS/V1")
        .filterBounds(point)
        .filter(ee.Filter.date(ee_date, ee_date.advance(1, "day")))
    )

    # Initialize default values (if no flood event exists at this coord/date)
    is_flooded = 0
    duration_val = 0
    label_type = "Spatial_Negative"

    # Check if an event exists
    event_img = gfd.first()
    has_event = gfd.size().gt(0)

    # Update values if event is found (using V10 logic)
    def get_event_info():
        flooded = event_img.select("flooded")
        duration = event_img.select("duration").unmask(0)

        # Classification logic from V10
        is_f = flooded.reduceRegion(ee.Reducer.first(), point, 250).get("flooded")
        dur = duration.reduceRegion(ee.Reducer.first(), point, 250).get("duration")

        # Conditionals for label_type
        # cls 2: High_Duration (>5), cls 1: Low_Duration (<=5)
        return ee.Dictionary(
            {
                "is_flooded": ee.Number(is_f).toInt(),
                "duration": dur,
                "label_type": ee.Algorithms.If(
                    ee.Number(dur).gt(5), "High_Duration", "Low_Duration"
                ),
            }
        )

    event_data = ee.Dictionary(
        ee.Algorithms.If(
            has_event,
            get_event_info(),
            {"is_flooded": 0, "duration": 0, "label_type": "Spatial_Negative"},
        )
    )

    # 4. TIME FEATURES
    month = ee_date.get("month")
    day_of_year = ee_date.getRelative("day", "year")
    season = month.subtract(1).divide(3).floor().add(1).mod(4).add(1)

    # 5. SAMPLE STATIC STACK
    static_values = static_stack.reduceRegion(
        reducer=ee.Reducer.first(), geometry=point, scale=250
    )

    # Combine everything
    final_dict = static_values.combine(event_data).combine(
        {
            "date": date_str,
            "month": month,
            "day_of_year": day_of_year,
            "season": season,
            "latitude": lat,
            "longitude": lon,
        }
    )

    return final_dict.getInfo()


import requests
from datetime import datetime, timedelta


def get_visual_crossing_rainfall(lat, lon, date_str, api_key):
    """
    Fetches rainfall features using Visual Crossing API aligned with GEE V14 logic.

    Args:
        lat (float): Latitude
        lon (float): Longitude
        date_str (str): Target date in 'YYYY-MM-DD'
        api_key (str): Your Visual Crossing API Key
    """

    # 1. Setup Date Windows
    target_dt = datetime.strptime(date_str, "%Y-%m-%d")
    start_date = (target_dt - timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = (target_dt + timedelta(days=2)).strftime("%Y-%m-%d")

    # 2. API Request
    # Timeline API: {location}/{date1}/{date2}
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{start_date}/{end_date}"
    params = {
        "unitGroup": "metric",
        "include": "days",
        "key": api_key,
        "contentType": "json",
        "elements": "datetime,precip",
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {"error": f"API Request failed: {response.text}"}

    data = response.json()
    days = data.get("days", [])

    # Create a lookup dictionary for precipitation by date
    precip_map = {day["datetime"]: day.get("precip", 0) for day in days}

    rain_features = {}

    # --- A. Past Daily Rainfall (Days -1 to -15) ---
    for i in range(1, 16):
        d = (target_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        rain_features[f"rain_day_minus_{i}"] = precip_map.get(d, 0)

    # --- B. Forecast Rainfall (Days 0 to +2) ---
    # Day 0 is the event day (forecast_day_plus_0)
    for i in range(0, 3):
        d = (target_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        rain_features[f"forecast_day_plus_{i}"] = precip_map.get(d, 0)

    # --- C. Soil Memory (Days -16 to -30 cumulative) ---
    soil_memory = 0
    for i in range(16, 31):
        d = (target_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        soil_memory += precip_map.get(d, 0)

    rain_features["soil_memory_30d"] = soil_memory

    # --- Metadata ---
    rain_features["latitude"] = lat
    rain_features["longitude"] = lon
    rain_features["date"] = date_str

    return rain_features


# --- Example Usage ---
# API_KEY = "YOUR_VISUAL_CROSSING_KEY"
# rainfall_data = get_visual_crossing_rainfall(26.14, 85.36, "2023-08-15", API_KEY)
# print(rainfall_data)


static_features = get_point_flood_features(lat, lon, date_str)
rain_features = get_visual_crossing_rainfall(lat, lon, date_str, API_KEY)

# Combine them into one record
final_dataset_row = {**static_features, **rain_features}

print(final_dataset_row)


def get_flood_prediction(
    input_data, bundle_path="flood_model_bundle_V2.pkl", threshold=0.5
):  # threshold = 0.436 or 0.596
    """
    Predicts flood probability for a single data point.

    Parameters:
    - input_data (dict): The raw data dictionary.
    - bundle_path (str): Path to the saved joblib bundle.
    - threshold (float): Probability threshold for classification.
    """
    # 1. Load the bundle
    bundle = joblib.load(bundle_path)
    model = bundle["model"]
    scaler = bundle["scaler"]
    all_features = bundle["features"]
    cat_features = bundle["categorical_features"]
    best_iter = bundle["best_iteration"]

    # 2. Convert dict to DataFrame
    df = pd.DataFrame([input_data])
    df["date"] = pd.to_datetime(df["date"])

    # 3. Feature Engineering (Matches Training Logic)
    # --- Rainfall Aggregations ---
    df["rain_sum_3d"] = df[[f"rain_day_minus_{i}" for i in range(1, 4)]].sum(axis=1)
    df["rain_sum_7d"] = df[[f"rain_day_minus_{i}" for i in range(1, 8)]].sum(axis=1)
    df["rain_sum_15d"] = df[[f"rain_day_minus_{i}" for i in range(1, 16)]].sum(axis=1)

    # --- Intensity ---
    df["rain_max_3d"] = df[[f"rain_day_minus_{i}" for i in range(1, 4)]].max(axis=1)
    df["rain_max_7d"] = df[[f"rain_day_minus_{i}" for i in range(1, 8)]].max(axis=1)
    df["rain_mean_3d"] = df["rain_sum_3d"] / 3
    df["rain_mean_7d"] = df["rain_sum_7d"] / 7
    df["rain_std_7d"] = (
        df[[f"rain_day_minus_{i}" for i in range(1, 8)]].std(axis=1).fillna(0)
    )
    df["rain_std_15d"] = (
        df[[f"rain_day_minus_{i}" for i in range(1, 16)]].std(axis=1).fillna(0)
    )

    # --- Temporal Patterns ---
    df["rain_trend"] = df["rain_day_minus_1"] - df["rain_day_minus_7"]
    df["rain_recent_vs_week"] = df["rain_sum_3d"] / (df["rain_sum_7d"] + 1)
    df["rain_acceleration"] = df["rain_day_minus_1"] - df["rain_day_minus_3"]
    df["recent_max_intensity"] = df[
        ["rain_day_minus_1", "rain_day_minus_2", "rain_day_minus_3"]
    ].max(axis=1)

    # --- API ---
    weights = np.exp(-0.1 * np.arange(15))
    rain_cols = [f"rain_day_minus_{i}" for i in range(1, 16)]
    df["API"] = df[rain_cols].mul(weights).sum(axis=1)
    weights_fast = np.exp(-0.3 * np.arange(7))
    df["API_fast_7d"] = (
        df[[f"rain_day_minus_{i}" for i in range(1, 8)]].mul(weights_fast).sum(axis=1)
    )

    # --- Topographic Interactions ---
    df["TWI_x_rain3d"] = df["TWI"] * df["rain_sum_3d"]
    df["TWI_x_rain7d"] = df["TWI"] * df["rain_sum_7d"]
    df["TWI_x_API"] = df["TWI"] * df["API"]
    df["slope_x_intensity"] = df["slope"] * df["rain_max_3d"]
    df["slope_x_rain7d"] = df["slope"] * df["rain_sum_7d"]
    df["elevation_x_rain3d"] = df["elevation"] * df["rain_sum_3d"]
    df["elevation_x_rain7d"] = df["elevation"] * df["rain_sum_7d"]
    df["flat_x_rain"] = (1 / (df["slope"] + 0.1)) * df["rain_sum_3d"]

    # --- Distance Interactions ---
    df["dist_x_rain3d"] = df["dist_to_river"] * df["rain_sum_3d"]
    df["dist_x_rain7d"] = df["dist_to_river"] * df["rain_sum_7d"]
    df["dist_x_soil"] = df["dist_to_river"] * df["soil_memory_30d"]
    df["dist_x_TWI"] = df["dist_to_river"] * df["TWI"]
    df["near_river"] = (df["dist_to_river"] < 1).astype(int)
    df["near_river_x_rain"] = df["near_river"] * df["rain_sum_3d"]

    # --- Soil Saturation ---
    df["saturation_index"] = df["soil_memory_30d"] + df["rain_sum_7d"]
    df["saturation_ratio"] = df["rain_sum_3d"] / (df["soil_memory_30d"] + 1)
    df["soil_vs_recent"] = df["soil_memory_30d"] / (df["rain_sum_3d"] + 1)
    df["total_water"] = df["soil_memory_30d"] + df["rain_sum_15d"]

    # --- Forecast Features ---
    df["forecast_sum"] = df[
        ["forecast_day_plus_0", "forecast_day_plus_1", "forecast_day_plus_2"]
    ].sum(axis=1)
    df["forecast_max"] = df[
        ["forecast_day_plus_0", "forecast_day_plus_1", "forecast_day_plus_2"]
    ].max(axis=1)
    df["forecast_mean"] = df["forecast_sum"] / 3
    df["total_rain_window"] = df["rain_sum_7d"] + df["forecast_sum"]

    # --- Compound Risks ---
    df["compound_risk_1"] = df["TWI"] * df["rain_sum_3d"] / (df["dist_to_river"] + 0.1)
    df["compound_risk_2"] = df["API"] * df["saturation_index"] / (df["slope"] + 0.1)
    df["compound_risk_3"] = df["TWI"] * df["total_water"] / (df["elevation"].abs() + 1)

    # --- Temporal and Consecutive ---
    df["day_of_year"] = df["date"].dt.dayofyear
    df["season_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["season_cos"] = np.cos(2 * np.pi * df["month"] / 12)
    df["consecutive_rain"] = 0
    for i in range(1, 4):
        df["consecutive_rain"] += (df[f"rain_day_minus_{i}"] > 10).astype(int)

    # 4. Final Preparation
    # Select features in training order and fill missing
    X = df.reindex(columns=all_features).fillna(0)

    # 5. Apply Scaling (Numeric only)
    numeric_to_scale = [f for f in all_features if f not in cat_features]
    X[numeric_to_scale] = scaler.transform(X[numeric_to_scale])

    # 6. Predict
    prob = model.predict(X, num_iteration=best_iter)[0]
    prediction = 1 if prob >= threshold else 0

    return {
        "flood_probability": float(prob),
        "is_flooded": bool(prediction),
        "threshold_used": threshold,
    }


result = get_flood_prediction(final_dataset_row)
print(result)


# def full_pipeline(lat, lon, date_str):
#     static_features = get_point_flood_features(lat, lon, date_str)
#     rain_features = get_visual_crossing_rainfall(lat, lon, date_str, API_KEY)

#     # Combine them into one record
#     final_dataset_row = {**static_features, **rain_features}
#     result = get_flood_prediction(final_dataset_row)
#     return result


# print(full_pipeline(lat, lon, date_str=date_str))
