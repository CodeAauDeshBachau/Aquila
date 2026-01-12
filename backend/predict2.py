import numpy as np
import pandas as pd
import tensorflow as tf
import joblib
from typing import Dict, Tuple
import ee
import math
import pandas as pd
import numpy as np
import joblib
import lightgbm as lgb


def predict_single_event(
    event_dict: Dict,
    model_path: str = "flood_model_output/best_model.keras",
    artifacts_path: str = "flood_model_output/deployment_artifacts.joblib",
) -> Dict:
    """
    Predict flood probability for a single event.

    Args:
        event_dict: Dictionary containing event data with keys:
            - Temporal: rain_day_minus_1 to rain_day_minus_15,
                       forecast_day_plus_0 to forecast_day_plus_2
            - Static: longitude, latitude, elevation, slope, TWI,
                     dist_to_river, soil_memory_30d, landcover
        model_path: Path to trained model (.keras file)
        artifacts_path: Path to deployment artifacts (.joblib file)

    Returns:
        Dictionary containing:
            - 'flood_probability': Float between 0 and 1
            - 'prediction': 'Flood' or 'No Flood'
            - 'confidence': Confidence percentage
            - 'input_summary': Summary of input data
    """

    # Load model and artifacts
    model = tf.keras.models.load_model(model_path)
    artifacts = joblib.load(artifacts_path)

    # Extract feature column names and scalers
    temporal_cols = artifacts["feature_columns"]["temporal"]
    static_cols = artifacts["feature_columns"]["static"]
    temp_scaler = artifacts["scalers"]["temporal"]
    static_scaler = artifacts["scalers"]["static"]

    # Validate required fields
    required_fields = temporal_cols + static_cols
    missing_fields = [field for field in required_fields if field not in event_dict]

    if missing_fields:
        raise ValueError(f"Missing required fields: {missing_fields}")

    # Extract temporal features (18 values)
    temporal_values = [event_dict[col] for col in temporal_cols]
    X_temp = np.array(temporal_values).reshape(1, -1)  # Shape: (1, 18)

    # Extract static features (8 values)
    static_values = [event_dict[col] for col in static_cols]
    X_static = np.array(static_values).reshape(1, -1)  # Shape: (1, 8)

    # Scale temporal data
    X_temp_flat = X_temp.flatten().reshape(-1, 1)  # Shape: (18, 1)
    X_temp_scaled = temp_scaler.transform(X_temp_flat)
    X_temp = X_temp_scaled.reshape(1, 18, 1)  # Shape: (1, 18, 1)

    # Scale static features
    X_static = static_scaler.transform(X_static)  # Shape: (1, 8)

    # Make prediction
    probability = model.predict([X_temp, X_static], verbose=0)[0][0]

    # Determine prediction and confidence
    prediction = "Flood" if probability >= 0.5 else "No Flood"
    confidence = probability * 100 if probability >= 0.5 else (1 - probability) * 100

    # Create input summary
    input_summary = {
        "location": f"({event_dict.get('latitude', 'N/A')}, {event_dict.get('longitude', 'N/A')})",
        "date": event_dict.get("date", "N/A"),
        "elevation": f"{event_dict.get('elevation', 'N/A')}m",
        "recent_rainfall": f"{sum([event_dict.get(f'rain_day_minus_{i}', 0) for i in range(1, 4)])} mm (last 3 days)",
        "soil_memory": f"{event_dict.get('soil_memory_30d', 'N/A')} mm",
    }

    # Return result
    result = {
        "flood_probability": float(probability),
        "prediction": prediction,
        "confidence": f"{confidence:.1f}%",
        "input_summary": input_summary,
        "threshold_used": 0.5,
    }

    return result


def predict_with_custom_threshold(
    event_dict: Dict,
    threshold: float = 0.5,
    model_path: str = "flood_model_output/best_model.keras",
    artifacts_path: str = "flood_model_output/deployment_artifacts.joblib",
) -> Dict:
    """
    Predict flood with custom threshold.

    Args:
        event_dict: Event data dictionary
        threshold: Custom classification threshold (0.0 to 1.0)
        model_path: Path to model
        artifacts_path: Path to artifacts

    Returns:
        Dictionary with prediction results
    """

    # Get base prediction
    result = predict_single_event(event_dict, model_path, artifacts_path)

    # Apply custom threshold
    probability = result["flood_probability"]
    prediction = "Flood" if probability >= threshold else "No Flood"
    confidence = (
        probability * 100 if probability >= threshold else (1 - probability) * 100
    )

    result["prediction"] = prediction
    result["confidence"] = f"{confidence:.1f}%"
    result["threshold_used"] = threshold

    return result


def get_risk_level(probability: float) -> str:
    """
    Convert probability to risk level.

    Args:
        probability: Flood probability (0.0 to 1.0)

    Returns:
        Risk level string
    """
    if probability < 0.2:
        return "Very Low"
    elif probability < 0.4:
        return "Low"
    elif probability < 0.6:
        return "Moderate"
    elif probability < 0.8:
        return "High"
    else:
        return "Very High"


def predict_with_detailed_output(
    event_dict: Dict,
    model_path: str = "flood_model_output/best_model.keras",
    artifacts_path: str = "flood_model_output/deployment_artifacts.joblib",
) -> Dict:
    """
    Predict flood with detailed analysis.

    Args:
        event_dict: Event data dictionary
        model_path: Path to model
        artifacts_path: Path to artifacts

    Returns:
        Dictionary with detailed prediction and risk analysis
    """

    # Get base prediction
    result = predict_single_event(event_dict, model_path, artifacts_path)
    probability = result["flood_probability"]

    # Add risk analysis
    result["risk_level"] = get_risk_level(probability)

    # Add rainfall analysis
    rainfall_last_3_days = sum(
        [event_dict.get(f"rain_day_minus_{i}", 0) for i in range(1, 4)]
    )
    rainfall_last_7_days = sum(
        [event_dict.get(f"rain_day_minus_{i}", 0) for i in range(1, 8)]
    )
    rainfall_last_15_days = sum(
        [event_dict.get(f"rain_day_minus_{i}", 0) for i in range(1, 16)]
    )

    result["rainfall_analysis"] = {
        "last_3_days": f"{rainfall_last_3_days:.1f} mm",
        "last_7_days": f"{rainfall_last_7_days:.1f} mm",
        "last_15_days": f"{rainfall_last_15_days:.1f} mm",
        "soil_memory_30d": f"{event_dict.get('soil_memory_30d', 0):.1f} mm",
    }

    # Add location context
    result["location_context"] = {
        "coordinates": f"({event_dict.get('latitude', 'N/A')}, {event_dict.get('longitude', 'N/A')})",
        "elevation": f"{event_dict.get('elevation', 'N/A')} m",
        "slope": f"{event_dict.get('slope', 'N/A')}°",
        "distance_to_river": f"{event_dict.get('dist_to_river', 'N/A')} m",
        "topographic_wetness_index": f"{event_dict.get('TWI', 'N/A')}",
    }

    # Add forecast
    forecast_rainfall = sum(
        [event_dict.get(f"forecast_day_plus_{i}", 0) for i in range(0, 3)]
    )
    result["forecast"] = {
        "next_3_days": f"{forecast_rainfall:.1f} mm",
        "day_0": f"{event_dict.get('forecast_day_plus_0', 0):.1f} mm",
        "day_1": f"{event_dict.get('forecast_day_plus_1', 0):.1f} mm",
        "day_2": f"{event_dict.get('forecast_day_plus_2', 0):.1f} mm",
    }

    # Add recommendation
    if probability >= 0.8:
        result["recommendation"] = (
            "URGENT: High flood risk. Immediate evacuation advised."
        )
    elif probability >= 0.6:
        result["recommendation"] = (
            "WARNING: Moderate to high flood risk. Prepare for potential evacuation."
        )
    elif probability >= 0.4:
        result["recommendation"] = (
            "CAUTION: Moderate flood risk. Monitor conditions closely."
        )
    elif probability >= 0.2:
        result["recommendation"] = (
            "ADVISORY: Low to moderate flood risk. Stay informed."
        )
    else:
        result["recommendation"] = "Normal conditions. Continue routine monitoring."

    return result


# main below
# lat = 27.806678
# lon = 84.905390

# 2.535036, 45.244423
# 34.250391, 65.993110


#
# 28.908200, 82.278749
# 27.806678, 84.905390
# date_str = "2024-09-29"
# date_str = "2025-12-01"
# API_KEY = "BDH7AMTHKFDJWJTU8QGGEV877"
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


def initialize():
    ee.Authenticate()
    ee.Initialize(project="aquila-478516")


def get_prediction(lat, lon, date_str, API_KEY):

    # try:

    #     ee.Initialize(project="aquila-478516")
    # except Exception as e:
    #     ee.Authenticate()
    #     ee.Initialize(project="aquila-478516")
    ee.Authenticate()
    ee.Initialize(project="aquila-478516")

    static_features = get_point_flood_features(lat, lon, date_str)
    rain_features = get_visual_crossing_rainfall(lat, lon, date_str, API_KEY)

    # Combine them into one record
    final_dataset_row = {**static_features, **rain_features}

    # print(final_dataset_row)

    result_detailed = predict_with_detailed_output(final_dataset_row)
    return result_detailed


# print(f"\nRISK ASSESSMENT:")
# print(f"  Probability: {result_detailed['flood_probability']:.3f}")
# print(f"  Risk Level: {result_detailed['risk_level']}")
# print(f"  Prediction: {result_detailed['prediction']}")

# print(f"\nRAINFALL ANALYSIS:")
# for key, value in result_detailed["rainfall_analysis"].items():
#     print(f"  {key.replace('_', ' ').title()}: {value}")

# print(f"\nLOCATION CONTEXT:")
# for key, value in result_detailed["location_context"].items():
#     print(f"  {key.replace('_', ' ').title()}: {value}")

# print(f"\nFORECAST:")
# for key, value in result_detailed["forecast"].items():
#     print(f"  {key.replace('_', ' ').title()}: {value}")

# print(f"\nRECOMMENDATION:")
# print(f"  {result_detailed['recommendation']}")

# print("\n" + "=" * 70)
