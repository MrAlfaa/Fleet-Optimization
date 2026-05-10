
import joblib
import pandas as pd
import numpy as np

bundle = joblib.load("demand_forecasting_model_bundle.joblib")

models = bundle["final_prophet_models"]
adjacency = bundle["adjacency"]
top_zones = bundle["top_zones"]
alpha = bundle["configuration"]["alpha_spatial_influence"]

def apply_graph_enhancement_to_forecast(baseline_df, adjacency, alpha=0.25):
    enhanced_rows = []
    forecast_lookup = baseline_df.set_index(["zone_id", "ds"])["yhat"].to_dict()

    for _, row in baseline_df.iterrows():
        zone = row["zone_id"]
        ds = row["ds"]
        base_yhat = row["yhat"]

        neighbors = adjacency.get(zone, [])

        if len(neighbors) == 0:
            graph_yhat = base_yhat
        else:
            weighted_neighbor_forecast = 0
            total_weight = 0

            for n in neighbors:
                neighbor_zone = n["neighbor"]
                weight = n["weight"]

                neighbor_yhat = forecast_lookup.get((neighbor_zone, ds), None)

                if neighbor_yhat is not None:
                    weighted_neighbor_forecast += weight * neighbor_yhat
                    total_weight += weight

            if total_weight > 0:
                weighted_neighbor_forecast = weighted_neighbor_forecast / total_weight
                graph_yhat = ((1 - alpha) * base_yhat) + (alpha * weighted_neighbor_forecast)
            else:
                graph_yhat = base_yhat

        enhanced_rows.append({
            "zone_id": zone,
            "ds": str(ds),
            "baseline_yhat": round(float(base_yhat), 2),
            "graph_enhanced_yhat": round(float(max(0, graph_yhat)), 2)
        })

    return pd.DataFrame(enhanced_rows)

def forecast_demand(days=7):
    baseline_rows = []

    for zone, model in models.items():
        future = model.make_future_dataframe(periods=days, freq="D")
        forecast = model.predict(future)

        max_history_date = forecast["ds"].max() - pd.Timedelta(days=days)
        future_forecast = forecast[forecast["ds"] > max_history_date].copy()
        future_forecast["zone_id"] = zone
        future_forecast["yhat"] = future_forecast["yhat"].clip(lower=0)

        baseline_rows.append(future_forecast[["zone_id", "ds", "yhat"]])

    baseline_df = pd.concat(baseline_rows, ignore_index=True)

    enhanced_df = apply_graph_enhancement_to_forecast(
        baseline_df,
        adjacency,
        alpha=alpha
    )

    return enhanced_df.to_dict(orient="records")
