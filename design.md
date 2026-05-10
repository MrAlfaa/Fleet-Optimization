# FleetOpt AI - Google Stitch Web UI Design Prompt

## Stitch Project

Project title: `FleetOpt AI - Web Admin Dashboard`

Created Stitch project:

```text
projects/519806286752247916
```

## Design System Prompt

Use this as the project design system or paste it before the screen-generation prompt if Stitch asks for a theme description.

```text
FleetOpt AI is a light enterprise operations dashboard for logistics fleet managers, route planners, and maintenance teams.

Design style:
- Light mode
- Professional SaaS operations dashboard
- Dense but readable information
- No marketing hero sections
- No decorative blobs, oversized gradients, or landing-page composition
- Persistent left sidebar
- Top command bar with search, date filter, alerts, and profile
- Map panels, tables, charts, status badges, timelines, and form panels
- Cards only for real dashboard widgets, tables, forms, maps, and status summaries

Color system:
- Primary logistics blue: #1D4ED8
- Primary dark/navy: #1E3A8A
- Success / low risk: #16A34A
- Warning / medium risk: #F59E0B
- Critical / high risk: #DC2626
- Info / active route: #0284C7
- Background: #F8FAFC
- Surface: #FFFFFF
- Muted surface: #F1F5F9
- Border: #CBD5E1
- Primary text: #0F172A
- Secondary text: #475569
- Muted text: #64748B

Typography:
- Font family: Inter
- Page title: 28px bold
- Section title: 18-20px bold
- Card metric: 24-28px bold
- Body/table: 14px regular or medium
- Labels/badges: 12px semibold
- Do not use negative letter spacing
- Do not scale font sizes using viewport width

Shape and spacing:
- Border radius: 8px
- Content padding: 24px
- Grid gap: 16px
- Use subtle borders and light shadows only

Product rules:
- Web dashboard only
- Do not design Flutter driver mobile screens
- Predictive maintenance model status must say: Placeholder baseline
- Demand forecasting model status must say: Placeholder moving average
- Do not claim trained ML accuracy
- Route planning must look like operational route optimization, not only Google Maps navigation
```

## Master Stitch Prompt

```text
Design a professional React web admin dashboard UI for “FleetOpt AI”, an AI-driven fleet optimization platform for logistics operations.

The product has three connected research components:
1. Predictive Maintenance: vehicle and part risk monitoring, maintenance history, service completion, risky part alerts.
2. Demand Forecasting: zone-level parcel demand forecasts, heatmaps, overloaded-zone detection, actual vs predicted comparison.
3. Dynamic Route Optimization: delivery order planning, vehicle/driver assignment, optimized routes, dispatch warnings, live trip monitoring.

Design a light enterprise operations dashboard, not a marketing website. The UI should feel like a logistics control center used daily by fleet managers, planners, and maintenance teams.

Visual style:
- Light mode
- Clean professional SaaS dashboard
- Dense but readable information
- Left sidebar navigation
- Top command bar with search, date filter, alerts, and user profile
- Cards only for actual dashboard widgets or list items, not decorative page sections
- Use map panels, tables, charts, badges, timelines, and status indicators
- Use clear status colors: green low risk, amber medium risk, red high/critical risk, blue active/neutral
- Typography: Inter
- Border radius: 8px
- Avoid oversized hero sections, decorative blobs, generic gradients, and landing-page composition

Create these desktop screens at 1440px width:

1. Login screen
- Brand: FleetOpt AI
- Email/password fields
- Role hint text: Admin, fleet manager, planner, maintenance staff
- Professional logistics-themed layout
- No marketing hero

2. Main Dashboard
- Fleet health summary
- Vehicles active, vehicles under maintenance, critical-risk vehicles, active routes
- Maintenance risk chart
- Demand forecast summary by zone
- Route efficiency metrics
- Recent alerts
- Live map preview

3. Vehicle Registry
- Vehicle table with number, model, type, assigned driver, mileage, status, risk
- Filters for status, vehicle type, risk level
- Add vehicle button
- Row actions: view, edit, maintenance

4. Vehicle Detail and Part Health
- Vehicle profile header
- Clickable vehicle parts/blueprint-style panel using cards for engine, battery, brake pads, tires, suspension, oil filter, clutch, radiator, lights
- Each part shows last service, failure count, risk level, predicted next maintenance date
- Maintenance timeline
- Mark as maintained action

5. Maintenance History
- Maintenance records table
- Add maintenance record form panel
- Service completion workflow
- Cost, mileage, service date, part, technician, notes
- Overdue and high-risk alerts

6. Predictive Maintenance Risk Dashboard
- Risk distribution across fleet
- High-risk vehicles/parts list
- Prediction confidence/model status badge showing “Placeholder baseline”
- Recommended maintenance windows
- Critical dispatch warning examples

7. Demand Forecast Dashboard
- Forecast by zone
- Daily/weekly forecast charts
- Overloaded zone detection
- What-if simulation controls: holiday, rain day, promotion day, manual demand spike
- Export forecast action
- Model status badge showing “Placeholder moving average”

8. Zone Demand Heatmap
- Large map panel with colored delivery zones
- Zone list side panel
- Predicted demand, actual demand, overload score
- Neighboring zone influence preview

9. Delivery Management
- Delivery order table
- Customer priority, time window, zone, location, assigned status
- Add delivery point action
- Batch select for route planning

10. Route Planning and Dispatch
- Select depot, vehicles, drivers, and delivery orders
- Optimized route result map
- Stop order list
- Route metrics: total distance, ETA, workload balance, vehicle capacity use
- Maintenance-risk warning if selected vehicle is high risk
- Dispatch/override action with reason field

11. Live Trip Monitoring
- Active trip map
- Driver/vehicle status cards
- Current location, next stop, ETA, completed stops
- Alerts for delay, issue report, weather warning, maintenance warning
- Trip event timeline

12. Alerts Center
- Alert list grouped by severity
- Filters for maintenance, route, demand, weather, driver issue
- Acknowledge alert action
- Critical alerts visually strong but not noisy

13. Reports and Model Status
- Maintenance report summary
- Route efficiency report
- Demand forecast report
- Model run history cards
- Metrics placeholders: accuracy, precision, recall, F1, MAE, RMSE, MAPE
- Clear labels that ML models are placeholders until trained

Navigation items:
Dashboard, Vehicles, Maintenance, Predictive Risk, Demand Forecast, Zones, Deliveries, Route Planning, Live Trips, Alerts, Reports, Admin.

Use realistic sample data:
- Vehicle numbers like CAB-1024, TRK-2041, VAN-3810
- Drivers with names
- Zones like Colombo Central, Nugegoda, Dehiwala, Malabe, Kaduwela
- Risk levels low, medium, high, critical
- Delivery stops with ETA and priority

The screens must be implementation-friendly for React:
- Reusable sidebar layout
- Reusable dashboard cards
- Reusable data tables
- Reusable status badges
- Reusable form panels
- Reusable map placeholder components
- Reusable chart cards
- Consistent spacing and component states
```

## Split Prompts If Stitch Input Is Too Long

### Prompt A - Authentication and Dashboard

```text
Using the FleetOpt AI design system, generate desktop web screens for:
1. Login screen
2. Main Dashboard

FleetOpt AI is a light enterprise logistics dashboard for fleet managers, planners, and maintenance teams. Use a left sidebar, top command bar, Inter typography, 8px radius, blue primary #1D4ED8, green low risk, amber medium risk, red high/critical risk, cool gray background #F8FAFC.

Login must include email/password, role hint text, professional logistics layout, and no marketing hero.

Dashboard must include fleet health summary, active vehicles, vehicles under maintenance, critical-risk vehicles, active routes, maintenance risk chart, demand forecast summary by zone, route efficiency metrics, recent alerts, and live map preview.
```

### Prompt B - Fleet and Maintenance

```text
Using the FleetOpt AI design system, generate desktop web screens for:
1. Vehicle Registry
2. Vehicle Detail and Part Health
3. Maintenance History
4. Predictive Maintenance Risk Dashboard

Use realistic vehicles CAB-1024, TRK-2041, VAN-3810 and drivers Nimal Perera, Kasun Silva, Amali Fernando, Dinesh Kumar.

The vehicle detail screen must include part-health cards for engine, battery, brake pads, tires, suspension, oil filter, clutch, radiator, and lights. Predictive maintenance screens must clearly show model status: Placeholder baseline. Do not claim trained ML accuracy.
```

### Prompt C - Demand, Routing, Alerts, Reports

```text
Using the FleetOpt AI design system, generate desktop web screens for:
1. Demand Forecast Dashboard
2. Zone Demand Heatmap
3. Delivery Management
4. Route Planning and Dispatch
5. Live Trip Monitoring
6. Alerts Center
7. Reports and Model Status

Use zones Colombo Central, Nugegoda, Dehiwala, Malabe, Kaduwela. Demand forecasting must show model status: Placeholder moving average. Route planning must show operational route optimization with stop order, route metrics, capacity use, maintenance-risk warning, and dispatch/override action. The reports screen must show placeholder metrics for accuracy, precision, recall, F1, MAE, RMSE, and MAPE without claiming trained model performance.
```

