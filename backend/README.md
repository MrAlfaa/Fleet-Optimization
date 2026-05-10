# AI Driven Fleet Optimization API

FastAPI backend foundation for the AI Driven Fleet Optimization research system. This backend is prepared for future React web dashboard, Flutter driver app, MongoDB Atlas, and ML inference integration.

## Phase 01 Scope

This phase adds only the backend foundation:

- FastAPI app startup
- environment-based configuration
- CORS setup for local web/mobile development
- MongoDB Atlas connection helpers using Motor
- health check endpoints
- reusable response helpers
- Phase 02 security placeholders
- organized ML artifact folders
- backend setup documentation

This phase does not implement authentication, vehicle APIs, prediction APIs, OR-Tools optimization, frontend integration, Flutter integration, or model loading.

## Phase 02 Scope

Phase 02 adds the backend authentication and user-management foundation:

- MongoDB-backed user collection
- unique email index for users
- bcrypt password hashing
- JWT access tokens
- protected current-user dependency
- role-based access dependencies
- auth endpoints
- admin user-management endpoints
- idempotent demo-user seed script

This phase still does not implement vehicle APIs, maintenance APIs, predictive maintenance APIs, demand forecasting APIs, route optimization APIs, frontend integration, Flutter integration, or ML model loading.

## Phase 03 Scope

Phase 03 adds the core fleet data APIs required for the Predictive Maintenance foundation:

- vehicle management
- default EV vehicle parts
- maintenance records
- basic alerts
- dashboard summaries
- protected role-based fleet routes
- idempotent demo fleet seed script

This phase still does not load ML artifacts, expose prediction APIs, implement demand forecasting APIs, implement route optimization APIs, or connect the React/Flutter frontends.

## Phase 04 Scope

Phase 04 integrates the EV predictive-maintenance artifact into backend inference APIs:

- lazy-loaded joblib model bundle
- prediction history stored in MongoDB
- vehicle and part risk updates from model output
- high/critical maintenance alert generation
- predictive fleet-risk summary endpoints
- predictive metrics inside the fleet dashboard summary

This phase does not implement demand forecasting APIs, route prediction APIs, route optimization APIs, IoT ingestion, or React/Flutter API integration.

## Phase 05 Scope

Phase 05 integrates the Demand Forecasting artifact outputs into backend APIs for the web dashboard and future route optimization:

- demand zone, forecast, planning recommendation, and model-run MongoDB collections
- artifact CSV/JSON import from `backend/app/ml_artifacts/demand_forecasting/`
- lazy demand model-bundle status/loading
- demand dashboard KPIs and export-ready forecast data
- high/very-high demand alerts without duplicate active alerts for the same zone/date

This phase does not implement route prediction APIs, OR-Tools optimization, frontend integration, Flutter integration, model retraining, or artifact modification.

## Folder Structure

```text
backend/
  app/
    main.py
    core/
      __init__.py
      config.py
      database.py
      security.py
    middleware/
      __init__.py
      auth_middleware.py
    models/
      __init__.py
      alert_model.py
      demand_model.py
      maintenance_model.py
      predictive_model.py
      user_model.py
      vehicle_model.py
      vehicle_part_model.py
    schemas/
      __init__.py
      alert_schema.py
      auth_schema.py
      dashboard_schema.py
      demand_schema.py
      maintenance_schema.py
      predictive_schema.py
      user_schema.py
      vehicle_schema.py
      vehicle_part_schema.py
    routes/
      __init__.py
      alert_routes.py
      auth_routes.py
      dashboard_routes.py
      demand_routes.py
      health_routes.py
      maintenance_routes.py
      predictive_routes.py
      user_routes.py
      vehicle_routes.py
    services/
      __init__.py
      alert_service.py
      auth_service.py
      dashboard_service.py
      demand_artifact_loader_service.py
      demand_forecasting_service.py
      maintenance_service.py
      ml_model_loader_service.py
      predictive_maintenance_service.py
      user_service.py
      vehicle_service.py
      vehicle_part_service.py
    ml_artifacts/
      predictive_maintenance/
      route_prediction/
      demand_forecasting/
    utils/
      __init__.py
      object_id.py
      pagination.py
      demand_utils.py
      response.py
      risk_utils.py
      validators.py
  scripts/
    seed_fleet_data.py
    seed_users.py
  requirements.txt
  .env.example
  README.md
```

## Environment Variables

Create a `.env` file from `.env.example` before running locally.

```env
APP_NAME=AI Driven Fleet Optimization API
APP_VERSION=1.0.0
ENVIRONMENT=development
API_PREFIX=/api
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DB_NAME=fleet_optimization
JWT_SECRET_KEY=replace-with-strong-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
CORS_ORIGINS=http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000
```

Notes:

- `MONGODB_URI` can be empty for health-check-only startup. Auth and user routes require MongoDB.
- `JWT_SECRET_KEY` must be replaced with a strong secret before shared testing or deployment.
- `CORS_ORIGINS` is a comma-separated list of allowed frontend origins.

## Setup and Run

Run these commands from the `backend` folder.

### Windows PowerShell

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

### macOS / Linux

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

## API Documentation

FastAPI documentation is available after startup:

- `http://localhost:8000/docs`
- `http://localhost:8000/redoc`

## Health Endpoints

When running locally with Uvicorn:

- `GET http://127.0.0.1:8000/`
- `GET http://127.0.0.1:8000/api/health`
- `GET http://127.0.0.1:8000/api/health/db`

Example response:

```json
{
  "success": true,
  "message": "Fleet Optimization API is running",
  "data": {
    "environment": "development"
  },
  "service": "AI Driven Fleet Optimization API",
  "version": "1.0.0"
}
```

If MongoDB is not configured, `/api/health/db` returns a clear `not_configured` status instead of crashing the app.

## Authentication Endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/change-password`
- `POST /api/auth/logout`

Login example:

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"admin@fleet.local\",\"password\":\"Admin@12345\"}"
```

Use the returned token with:

```text
Authorization: Bearer <access_token>
```

## User Management Endpoints

- `GET /api/users` - admin only
- `GET /api/users/{user_id}` - admin or same user
- `POST /api/users` - admin only
- `PUT /api/users/{user_id}` - admin or same user with limited profile fields
- `PATCH /api/users/{user_id}/deactivate` - admin only
- `PATCH /api/users/{user_id}/activate` - admin only
- `GET /api/users/drivers/list` - admin, fleet manager, or route planner

## Roles

- `admin` - full backend access
- `fleet_manager` - future fleet, maintenance, demand, route, alert, and report workflows
- `maintenance_manager` - future vehicle, part, maintenance, and predictive-alert workflows
- `route_planner` - future demand, route planning, delivery, and route analytics workflows
- `driver` - future mobile-focused assigned vehicle, route, alert, and status workflows

## Demo Users

Seed users are intended for local/demo testing only.

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@fleet.local` | `Admin@12345` |
| Fleet Manager | `fleet.manager@fleet.local` | `Fleet@12345` |
| Maintenance Manager | `maintenance.manager@fleet.local` | `Maint@12345` |
| Route Planner | `route.planner@fleet.local` | `Route@12345` |
| Driver | `driver@fleet.local` | `Driver@12345` |

Run the seed script after configuring MongoDB Atlas:

```bash
python scripts/seed_users.py
python scripts/seed_fleet_data.py
```

Run `seed_users.py` first because fleet maintenance records use the seeded admin user as `created_by`.

## Fleet API Endpoints

Vehicle endpoints:

- `GET /api/vehicles`
- `POST /api/vehicles`
- `GET /api/vehicles/{vehicle_id}`
- `PUT /api/vehicles/{vehicle_id}`
- `DELETE /api/vehicles/{vehicle_id}`
- `GET /api/vehicles/{vehicle_id}/parts`
- `POST /api/vehicles/{vehicle_id}/parts`
- `PUT /api/vehicles/parts/{part_id}`
- `PATCH /api/vehicles/{vehicle_id}/assign-driver/{driver_id}`

Maintenance endpoints:

- `GET /api/maintenance`
- `POST /api/maintenance`
- `GET /api/maintenance/summary/overview`
- `GET /api/maintenance/{record_id}`
- `PUT /api/maintenance/{record_id}`
- `PATCH /api/maintenance/{record_id}/complete`
- `PATCH /api/maintenance/{record_id}/cancel`

Alert endpoints:

- `GET /api/alerts`
- `POST /api/alerts`
- `GET /api/alerts/summary/overview`
- `GET /api/alerts/{alert_id}`
- `PATCH /api/alerts/{alert_id}/resolve`
- `PATCH /api/alerts/{alert_id}/dismiss`

Dashboard endpoints:

- `GET /api/dashboard/fleet-summary`
- `GET /api/dashboard/health-distribution`
- `GET /api/dashboard/maintenance-overview`
- `GET /api/dashboard/recent-alerts`
- `GET /api/dashboard/upcoming-maintenance`

## Phase 03 Permissions

- `admin`: all fleet, maintenance, alert, and dashboard actions
- `fleet_manager`: create/update vehicles, view/create maintenance, create alerts, view dashboard
- `maintenance_manager`: manage vehicle parts and maintenance, create alerts, view dashboard
- `route_planner`: view vehicles and alerts for planning; cannot edit maintenance
- `driver`: blocked from admin fleet APIs in this phase

## Phase 03 API Examples

Use a Bearer token from `/api/auth/login`.

Create vehicle:

```bash
curl -X POST "http://localhost:8000/api/vehicles" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"vehicle_code\":\"EV-FLEET-009\",\"registration_number\":\"WP-EV-1009\",\"vehicle_type\":\"electric_van\",\"brand\":\"BYD\",\"model\":\"T3\",\"year\":2024,\"fuel_type\":\"electric\",\"current_mileage\":1200,\"battery_capacity_kwh\":50}"
```

List vehicles:

```bash
curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/vehicles?page=1&limit=10"
```

Create maintenance record:

```bash
curl -X POST "http://localhost:8000/api/maintenance" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"vehicle_id\":\"<vehicle_id>\",\"part_name\":\"Battery Pack\",\"maintenance_type\":\"inspection\",\"issue_type\":\"Routine inspection\",\"service_date\":\"2026-05-10T09:00:00Z\",\"mileage_at_service\":1200,\"priority\":\"medium\"}"
```

Complete maintenance:

```bash
curl -X PATCH "http://localhost:8000/api/maintenance/<record_id>/complete" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"notes\":\"Completed successfully\"}"
```

Resolve alert:

```bash
curl -X PATCH "http://localhost:8000/api/alerts/<alert_id>/resolve" \
  -H "Authorization: Bearer <token>"
```

## Phase 04 Predictive Maintenance ML Integration

Phase 04 integrates the existing EV predictive-maintenance artifact as a lazy-loaded backend inference service. The backend now exposes real predictive-maintenance APIs, saves prediction history, updates vehicle and part risk state, creates high/critical maintenance alerts, and adds predictive metrics to the fleet dashboard summary.

Implemented files include:

- `app/models/predictive_model.py`
- `app/schemas/predictive_schema.py`
- `app/routes/predictive_routes.py`
- `app/services/ml_model_loader_service.py`
- `app/services/predictive_maintenance_service.py`
- `app/utils/risk_utils.py`

The detected predictive-maintenance artifact is:

```text
backend/app/ml_artifacts/predictive_maintenance/ev_predictive_maintenance_model_bundle.joblib
```

The model is not loaded at FastAPI startup. It is loaded lazily by the model-status or prediction endpoints and cached in memory after the first successful load. Missing or invalid artifacts return a clean model-unavailable response instead of crashing the backend.

### Predictive Maintenance Endpoints

All endpoints require a Bearer token for one of these roles:

- `admin`
- `fleet_manager`
- `maintenance_manager`

Available endpoints:

- `GET /api/predictive-maintenance/model/status`
- `POST /api/predictive-maintenance/predict`
- `POST /api/predictive-maintenance/predict-batch`
- `GET /api/predictive-maintenance/predictions`
- `GET /api/predictive-maintenance/predictions/{prediction_id}`
- `GET /api/predictive-maintenance/vehicle/{vehicle_id}/history`
- `GET /api/predictive-maintenance/fleet-risk-summary`
- `GET /api/predictive-maintenance/input-template`
- `POST /api/predictive-maintenance/simulate/{vehicle_id}`

### Model Status

```bash
curl -X GET "http://localhost:8000/api/predictive-maintenance/model/status" \
  -H "Authorization: Bearer <token>"
```

The response reports artifact path, artifact existence, loaded status, available bundle keys, required feature count, required feature names, and the metrics snapshot.

### Manual Prediction Example

```bash
curl -X POST "http://localhost:8000/api/predictive-maintenance/predict" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"vehicle_id\":\"<vehicle_id>\",\"input_source\":\"manual\",\"sensor_data\":{\"SoC\":65,\"SoH\":92,\"Battery_Voltage\":390,\"Battery_Current\":55,\"Battery_Temperature\":35,\"Charge_Cycles\":450,\"Motor_Temperature\":70,\"Motor_Vibration\":0.3,\"Motor_Torque\":180,\"Motor_RPM\":3200,\"Power_Consumption\":22,\"Brake_Pad_Wear\":35,\"Brake_Pressure\":60,\"Reg_Brake_Efficiency\":78,\"Tire_Pressure\":34,\"Tire_Temperature\":38,\"Suspension_Load\":70,\"Ambient_Temperature\":30,\"Ambient_Humidity\":72,\"Load_Weight\":850,\"Driving_Speed\":48,\"Distance_Traveled\":42000,\"Idle_Time\":8,\"Route_Roughness\":0.4}}"
```

Example response shape:

```json
{
  "success": true,
  "message": "Predictive maintenance prediction completed",
  "data": {
    "vehicle_id": "mongo_vehicle_id",
    "failure_prediction": 1,
    "failure_probability": 0.82,
    "risk_level": "critical",
    "maintenance_type_name": "Battery system maintenance",
    "predicted_rul": 52.4,
    "rul_unit": "hours",
    "next_maintenance_date": "2026-05-12T08:00:00+00:00",
    "recommended_action": "Immediate inspection required before dispatch.",
    "alert_created": true,
    "prediction_id": "mongo_prediction_id"
  }
}
```

### Simulated Prediction

Use this endpoint for demos until IoT ingestion is implemented:

```bash
curl -X POST "http://localhost:8000/api/predictive-maintenance/simulate/<vehicle_id>" \
  -H "Authorization: Bearer <token>"
```

The service generates realistic EV sensor values using the selected vehicle mileage, runs the model, saves the prediction, updates vehicle/part risk where possible, and creates a maintenance alert for high or critical risk.

### Model Limitations

The current artifact includes failure classification, maintenance-type prediction, and RUL regression outputs. The RUL model should be treated as lower-confidence because the artifact metrics show weak RUL performance, including negative `r2`. Use RUL as a planning hint, not as a final operational guarantee.

No IoT ingestion, real-time telemetry pipeline, demand forecasting API, route prediction API, or OR-Tools optimizer is implemented in this phase.

## Phase 05 Demand Forecasting Integration

Phase 05 exposes zone-wise demand forecasts and fleet planning recommendations using the extracted demand-forecasting artifacts.

Artifact folder:

```text
backend/app/ml_artifacts/demand_forecasting/
```

Detected files:

- `demand_forecasting_model_bundle.joblib`
- `demand_forecasting_metrics.json`
- `future_demand_forecast.csv`
- `fleet_planning_recommendations.csv`
- `zone_metadata.csv`
- `zone_adjacency_graph.json`
- `zone_daily_demand_training_data.csv`
- `backend_demand_forecasting_example.py`
- `README.txt`

### Demand Endpoints

All demand endpoints require one of these roles:

- `admin`
- `fleet_manager`
- `route_planner`

Available endpoints:

- `GET /api/demand/model/status`
- `GET /api/demand/model/metrics`
- `POST /api/demand/import-artifacts`
- `GET /api/demand/zones`
- `GET /api/demand/forecasts`
- `GET /api/demand/forecasts/{zone_id}`
- `POST /api/demand/refresh`
- `GET /api/demand/planning-recommendations`
- `GET /api/demand/dashboard-summary`
- `GET /api/demand/adjacency-graph`
- `GET /api/demand/export`

### Test Flow

1. Login as `admin@fleet.local` or `route.planner@fleet.local`.
2. Check artifact/model status.
3. Import artifact forecasts.
4. Review dashboard summary.
5. List forecasts and planning recommendations.

```bash
curl -X GET "http://localhost:8000/api/demand/model/status" \
  -H "Authorization: Bearer <token>"
```

```bash
curl -X POST "http://localhost:8000/api/demand/import-artifacts" \
  -H "Authorization: Bearer <token>"
```

```bash
curl -X GET "http://localhost:8000/api/demand/forecasts?zone_id=SP_sao_paulo&page=1&limit=10" \
  -H "Authorization: Bearer <token>"
```

```bash
curl -X GET "http://localhost:8000/api/demand/planning-recommendations?zone_id=SP_sao_paulo" \
  -H "Authorization: Bearer <token>"
```

### Refresh Example

```json
{
  "days": 30,
  "save_to_database": true,
  "source": "artifact"
}
```

Expected response shape:

```json
{
  "success": true,
  "message": "Demand forecasts imported successfully",
  "data": {
    "zones_imported": 10,
    "forecast_records": 300,
    "planning_records": 300,
    "model_run_id": "..."
  }
}
```

### Route Optimization Usage

Future route optimization should consume:

- zone-level forecast rows from `/api/demand/forecasts`
- required vehicle estimates from `/api/demand/planning-recommendations`
- overloaded zone indicators from `/api/demand/dashboard-summary`
- zone-neighbor influence data from `/api/demand/adjacency-graph`

### Model Limitation

The current artifact metrics show Graph-Enhanced Prophet performing worse than the baseline Prophet on the provided evaluation metrics. The backend exposes both metric groups transparently and keeps direct Prophet model refresh as best-effort. If serialized Prophet inference fails in the runtime environment, `/api/demand/refresh` falls back to artifact CSV forecasts instead of crashing.

## MongoDB Atlas Configuration

For Phase 02 database work:

1. Create a MongoDB Atlas cluster.
2. Add the local IP address to Atlas network access.
3. Create a database user with a strong password.
4. Set `MONGODB_URI` in `.env`.
5. Set `MONGODB_DB_NAME=fleet_optimization` or the chosen production database name.

Do not commit real MongoDB credentials or JWT secrets.

## ML Artifact Folders

The trained artifact ZIP files were extracted only for future integration. The backend does not import, load, execute, or test these model files in Phase 01.

### Predictive Maintenance

Source ZIP:

```text
Data_Sets/Predictive_Meintains_Data_Set/ev_pm_artifacts.zip
```

Extracted to:

```text
backend/app/ml_artifacts/predictive_maintenance/
```

Files:

- `ev_predictive_maintenance_features.json`
- `ev_predictive_maintenance_metrics.json`
- `ev_predictive_maintenance_model_bundle.joblib`
- `README.txt`

### Route Prediction

Source ZIP:

```text
Data_Sets/Route_Optimization/route_prediction_artifacts.zip
```

Extracted to:

```text
backend/app/ml_artifacts/route_prediction/
```

Files:

- `backend_route_prediction_example.py`
- `README.txt`
- `route_prediction_metrics.json`
- `route_prediction_model_bundle.joblib`
- `route_prediction_schema.json`

### Demand Forecasting

Source ZIP:

```text
Data_Sets/Demand Forcasting/demand_forecasting_artifacts.zip
```

Extracted to:

```text
backend/app/ml_artifacts/demand_forecasting/
```

Files:

- `backend_demand_forecasting_example.py`
- `demand_forecasting_metrics.json`
- `demand_forecasting_model_bundle.joblib`
- `fleet_planning_recommendations.csv`
- `future_demand_forecast.csv`
- `README.txt`
- `zone_adjacency_graph.json`
- `zone_daily_demand_training_data.csv`
- `zone_metadata.csv`

## Existing Frontend and Mobile Integration Targets

The current applications remain frontend-only and use local mock services.

React web app:

- `Fleet_Web_App/frontend/src/services/authService.ts`
- `Fleet_Web_App/frontend/src/services/fleetService.ts`
- `Fleet_Web_App/frontend/src/services/forecastService.ts`
- `Fleet_Web_App/frontend/src/services/operationsService.ts`

Flutter mobile app:

- `Fleet_Mobile_App/frontend/lib/services/mock_auth_service.dart`
- `Fleet_Mobile_App/frontend/lib/services/mock_driver_service.dart`

These services are planned integration points for backend APIs in later phases.

## Planned Future Route Modules

The predictive-maintenance route module is implemented in Phase 04, the demand route module is implemented in Phase 05, and route/delivery modules are implemented in Phase 06. The following module remains intentionally not created yet:

- `mobile_routes.py`

## Phase 06: Route Prediction, Deliveries, and Route Optimization

Phase 06 adds ML-assisted route planning APIs without connecting the React or Flutter frontends yet.

Implemented:

- Delivery-order CRUD APIs under `/api/deliveries`.
- Route prediction model status, metrics, single-segment prediction, and batch prediction under `/api/routes`.
- Single-vehicle OR-Tools route optimization with ML route-cost support and distance fallback.
- Route plan and route segment persistence in MongoDB.
- Route dispatch/cancel workflow.
- Route dashboard metrics added to `/api/dashboard/fleet-summary` as `route_optimization`.
- EV CSV-based fleet enrichment seed script: `python scripts/seed_ev_csv_fleet_data.py`.

Route artifact path:

```text
backend/app/ml_artifacts/route_prediction/route_prediction_model_bundle.joblib
```

Detected route model features:

```text
agent_age_num, agent_rating_num, distance_km, hour, day_of_week, month,
is_weekend, weather, traffic, vehicle, area, category
```

Example route segment prediction:

```bash
curl -X POST "http://localhost:8000/api/routes/predict-segment" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d "{\"pickup_latitude\":6.9271,\"pickup_longitude\":79.8612,\"drop_latitude\":6.9147,\"drop_longitude\":79.9729,\"weather\":\"Cloudy\",\"traffic\":\"Medium\",\"vehicle_type\":\"electric_van\",\"area\":\"urban\",\"category\":\"parcel\",\"order_date\":\"2026-05-10\",\"order_time\":\"09:30:00\"}"
```

Example route optimization:

```json
{
  "depot_latitude": 6.9271,
  "depot_longitude": 79.8612,
  "depot_name": "Colombo Depot",
  "delivery_stops": [
    {
      "order_code": "ORD-001",
      "drop_latitude": 6.9147,
      "drop_longitude": 79.9729,
      "zone_id": "SP_sao_paulo",
      "priority": "medium"
    },
    {
      "order_code": "ORD-002",
      "drop_latitude": 6.902,
      "drop_longitude": 79.86,
      "zone_id": "SP_sao_paulo",
      "priority": "high"
    }
  ],
  "use_ml_cost": true,
  "include_demand_context": true,
  "include_maintenance_context": true,
  "save_route": true
}
```

Known limitation: Phase 06 intentionally supports stable single-vehicle route optimization only. Multi-vehicle CVRP, capacity constraints, real traffic APIs, and frontend/mobile API integration are later phases.

## Recommended Next Phases

1. Phase 07: connect React web mock services to backend APIs and enable frontend CRUD forms.
2. Phase 08: connect Flutter driver mock services to backend APIs.
3. Phase 09: implement real-time trip tracking and operational notifications.
4. Phase 10: harden deployment, monitoring, and production configuration.
