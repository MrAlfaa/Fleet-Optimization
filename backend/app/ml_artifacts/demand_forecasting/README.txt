
AI Driven Fleet Optimization - Component 03
Demand Forecasting Model Artifacts

Dataset:
Olist Brazilian E-Commerce Dataset

Model:
1. Baseline Prophet model per delivery zone
2. Graph-Enhanced Prophet forecasting using spatial adjacency graph

Purpose:
Predict future parcel/order demand per delivery zone.
Forecast output can be used by:
- Route Optimization module
- Fleet allocation module
- Delivery zone planning
- Vehicle requirement estimation

Files:
1. demand_forecasting_model_bundle.joblib
   Contains trained Prophet models, graph adjacency, metrics, and configuration.

2. demand_forecasting_metrics.json
   Baseline Prophet vs Graph-Enhanced Prophet evaluation metrics.

3. zone_daily_demand_training_data.csv
   Final zone-level daily demand training dataset.

4. zone_metadata.csv
   Zone latitude/longitude metadata.

5. zone_adjacency_graph.json
   Neighbor zone graph and influence weights.

6. future_demand_forecast.csv
   Next 30 days forecast.

7. fleet_planning_recommendations.csv
   Demand level and estimated vehicle requirements.

8. backend_demand_forecasting_example.py
   Example code for backend integration.

Important:
This model predicts zone-level demand.
It does not directly optimize routes.
Route optimization component should consume this forecast output.

Created at:
2026-05-09T21:32:09.422155
