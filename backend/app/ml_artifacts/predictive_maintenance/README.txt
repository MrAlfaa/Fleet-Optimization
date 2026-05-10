
EV Predictive Maintenance Model Bundle

Files:
1. ev_predictive_maintenance_model_bundle.joblib
   - Contains failure prediction model
   - Contains maintenance type model
   - Contains RUL regression model
   - Contains feature column order and metadata

2. ev_predictive_maintenance_metrics.json
   - Evaluation metrics for trained models

3. ev_predictive_maintenance_features.json
   - Required feature columns for prediction input

How to use:
- Load the model bundle using joblib.load()
- Prepare input data with the same feature columns
- Use failure_model.predict_proba() for failure probability
- Use maintenance_type_model.predict() for maintenance type
- Use rul_model.predict() for remaining useful life
