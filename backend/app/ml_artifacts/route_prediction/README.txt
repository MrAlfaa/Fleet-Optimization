
AI Driven Fleet Optimization - Component 02
ML-Assisted Route Optimization Model Artifacts

Dataset:
Kaggle Amazon Delivery Dataset
Slug: kaggle_amazon_delivery_dataset

Architecture:
ML predicts ETA and delay risk.
Route cost score is calculated from ETA + delay probability.
OR-Tools optimizer can use route_cost_score as edge cost.
Google Maps displays final route in the mobile app.

Files:
1. route_prediction_model_bundle.joblib
   Contains ETA model and delay risk model.

2. route_prediction_metrics.json
   Contains model evaluation metrics.

3. route_prediction_schema.json
   Contains feature columns and sample output.

4. backend_route_prediction_example.py
   Example code for backend integration.

Models:
- ETA Prediction: XGBoost Regressor
- Delay Risk Prediction: XGBoost Classifier

Important:
This model does not directly generate full route order.
It predicts route segment cost.
The final route sequence should be generated using OR-Tools / VRP optimizer.

Created at:
2026-05-09T20:58:23.894653
