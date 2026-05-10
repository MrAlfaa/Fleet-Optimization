
import re
import joblib
import numpy as np
import pandas as pd
from datetime import datetime

bundle = joblib.load("route_prediction_model_bundle.joblib")

eta_model = bundle["eta_model"]
delay_model = bundle["delay_model"]
feature_columns = bundle["feature_columns"]
detected = bundle["detected_columns"]

def clean_column_name(col):
    col = str(col).strip().lower()
    col = re.sub(r"[^a-z0-9]+", "_", col)
    col = re.sub(r"_+", "_", col)
    col = col.strip("_")
    return col

def haversine_distance_km(lat1, lon1, lat2, lon2):
    radius = 6371.0
    
    lat1 = np.radians(pd.to_numeric(lat1, errors="coerce"))
    lon1 = np.radians(pd.to_numeric(lon1, errors="coerce"))
    lat2 = np.radians(pd.to_numeric(lat2, errors="coerce"))
    lon2 = np.radians(pd.to_numeric(lon2, errors="coerce"))
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return radius * c

def prepare_input(input_dict):
    sample = pd.DataFrame([input_dict])
    sample.columns = [clean_column_name(c) for c in sample.columns]
    
    store_lat = detected["store_lat_col"]
    store_lon = detected["store_lon_col"]
    drop_lat = detected["drop_lat_col"]
    drop_lon = detected["drop_lon_col"]
    
    if all([store_lat, store_lon, drop_lat, drop_lon]):
        if all(c in sample.columns for c in [store_lat, store_lon, drop_lat, drop_lon]):
            sample["distance_km"] = haversine_distance_km(
                sample[store_lat],
                sample[store_lon],
                sample[drop_lat],
                sample[drop_lon]
            )
    
    order_date = detected["order_date_col"]
    order_time = detected["order_time_col"]
    
    if order_date in sample.columns and order_time in sample.columns:
        dt = pd.to_datetime(sample[order_date].astype(str) + " " + sample[order_time].astype(str), errors="coerce")
    else:
        dt = pd.Series([pd.to_datetime(datetime.now())])
    
    sample["hour"] = dt.dt.hour
    sample["day_of_week"] = dt.dt.dayofweek
    sample["month"] = dt.dt.month
    sample["is_weekend"] = sample["day_of_week"].isin([5, 6]).astype(int)
    
    for col in feature_columns:
        if col not in sample.columns:
            sample[col] = np.nan
    
    return sample[feature_columns]

def predict_route_cost(input_dict, delay_penalty=0.30):
    X = prepare_input(input_dict)
    
    eta = float(eta_model.predict(X)[0])
    delay_prob = float(delay_model.predict_proba(X)[0][1])
    route_cost = eta * (1 + delay_prob * delay_penalty)
    
    return {
        "predicted_eta_minutes": round(eta, 2),
        "delay_probability": round(delay_prob, 4),
        "delay_prediction": int(delay_prob >= 0.5),
        "route_cost_score": round(route_cost, 2)
    }
