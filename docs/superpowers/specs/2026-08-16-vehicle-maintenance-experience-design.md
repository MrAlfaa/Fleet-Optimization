# Vehicle and Maintenance Experience Design

## Objective

Modernize the fleet vehicle and maintenance workflows without changing the existing role, prediction, route assignment, or delivery execution contracts. The design makes registration number and vehicle imagery the primary visual identity, converts maintenance history into a vehicle-centered workload view, and preserves route dispatch as the authoritative driver/vehicle assignment action.

## Scope

This change includes:

- authenticated local vehicle-image upload;
- a redesigned vehicle creation form;
- a structured EV subsystem health view;
- a vehicle-grouped maintenance registry;
- a vehicle-specific maintenance workspace;
- removal of implementation-facing labels such as `Backend API` from the web UI;
- removal of the Zones page Planning Signal card;
- clearer delivery-to-route assignment navigation.

It does not add direct ad hoc driver assignment to unrelated individual deliveries, cloud media storage, image editing, a new maintenance database model, or changes to ML artifacts.

## Vehicle Media Architecture

Vehicle images are uploaded to the existing FastAPI backend using authenticated multipart requests. Files are stored under `backend/media/vehicles/` using server-generated names. MongoDB stores only the public media path in `image_url`.

Accepted formats are JPEG, PNG, and WebP with a maximum size of 5 MB. Validation checks both content type and extension. Filenames supplied by users are never used as storage paths. A missing image uses a code-owned EV placeholder. Replacing an image removes the previous local image only when it is a managed vehicle-media file and is no longer referenced.

FastAPI exposes the media directory under `/media`. Vehicle list, detail, create, and update response contracts include nullable `image_url`. Existing vehicles remain valid without migration because the field is optional.

## Vehicle Registry and Creation

The vehicle creation experience uses three unframed sections inside one modal or drawer:

1. Vehicle Identity: image, registration number, internal fleet code, category, brand, model, and year.
2. EV Specifications: electric fuel type, battery capacity, and current mileage.
3. Operational State: vehicle status and health status. Driver assignment remains a separate controlled operation rather than part of basic vehicle creation.

The image control supports select, preview, replace, and remove. Registration number is the primary identifier and vehicle code is secondary. Duplicate registration and vehicle-code errors remain backend validated and are displayed beside the relevant fields.

The registry provides category and health/status filters. Vehicle rows or cards show image, registration number, fleet code, category, health, status, mileage, and next service information without implementation labels.

## Vehicle Detail and EV Health

The detail page starts with a vehicle identity band containing image, registration, fleet code, category, mileage, operational state, and key actions.

A compact health summary reports overall health, latest predictive risk, open maintenance count, and next service date. EV parts are displayed as a structured subsystem health list rather than equal repeated cards. Subsystems include Battery Pack, Battery Cooling System, Electric Motor/Drivetrain, Brakes, Tires, Suspension, Charging, Inverter, and Thermal Management.

Each subsystem row contains a Lucide icon, status, risk score visualization, last service date, next predicted maintenance date, and action summary. High and critical rows receive restrained semantic emphasis and reduced-motion-compatible animation. Selecting a subsystem reveals part history and linked maintenance records without changing the underlying part APIs.

The maintenance timeline remains visible beside the health list on desktop and follows it on narrow screens.

## Maintenance Fleet Registry

The Maintenance page becomes a vehicle-level workload table. Frontend aggregation groups existing maintenance records by `vehicle_id` and joins them with the vehicle list. This avoids introducing a duplicate persistence model or unnecessary backend endpoint in the initial implementation.

Each row shows:

- vehicle image, registration number, code, and category;
- vehicle health and operational status;
- total maintenance records;
- scheduled/in-progress work;
- pending or warning parts;
- overdue work;
- critical/high-priority work;
- last service and next due dates;
- outstanding planned cost where available.

Filters cover registration/code search, vehicle category, health, maintenance state, and overdue-only mode. Empty, loading, and API failure states use existing shared UI patterns.

Selecting a row navigates to `/maintenance/vehicle/:vehicleId`.

## Vehicle Maintenance Workspace

The maintenance workspace combines only data related to the selected vehicle:

- vehicle identity and image;
- readiness, health, and latest prediction state;
- open maintenance work;
- parts requiring attention;
- completed maintenance history;
- predictive-risk history when available;
- add, complete, update, and cancel maintenance actions allowed by the current role.

The existing `/vehicles/:vehicleId` page remains the general fleet detail view. The new maintenance route is operationally focused and links back to the vehicle detail page.

## Delivery and Assignment Workflow

Delivery Management owns order creation, map-based pickup/drop selection, filtering, and selection of pending orders. Selected order IDs can be passed to Route Planning through an `Assign to Route` or `Plan Selected` action.

Route Planning remains the authoritative assignment workflow:

1. Select pending delivery orders.
2. Select an eligible vehicle by MongoDB ID, displaying registration, category, and readiness.
3. Select an active enrolled driver by MongoDB ID, displaying username and assignment state.
4. Optimize the route.
5. Validate final vehicle and driver eligibility.
6. Dispatch the route.
7. Backend assigns the route and all linked delivery orders to the same driver and vehicle.
8. The driver mobile app receives only that assigned route and its ordered stops.

Direct independent assignment of different drivers or vehicles to deliveries in one route is not introduced because it would violate route consistency. Existing single-delivery assignment APIs remain backward compatible but are not the primary UI workflow.

## UI Cleanup

User-facing implementation labels such as `Backend API`, `Backend live`, `Route API`, and `History API` are removed across operational screens. Legitimate model status, fallback status, live connectivity, and actionable warnings remain visible using user-centered language.

The Zones page Planning Signal explanatory card is removed. Forecast metrics, calibration state, actual operational warnings, and refresh/import actions remain.

## Security and Error Handling

- Image upload requires the same admin/fleet-manager authorization as vehicle updates.
- File paths are server generated and confined to the media directory.
- Unsupported formats, empty files, oversized files, and invalid vehicle IDs return structured API errors.
- Frontend uploads use `FormData`; the API client must not force a JSON content type for multipart requests.
- Backend authorization remains authoritative for maintenance and assignment actions.
- Image upload failure does not create a partially configured vehicle. The UI creates the vehicle first only when the image is optional, then reports an explicit partial upload failure with a retry action, or uses a combined create flow if the existing service can support it cleanly.

## Testing

Backend tests cover optional image schema compatibility, upload authorization, MIME/size validation, generated path confinement, replacement behavior, and media URL serialization.

React tests cover vehicle adapters, image upload form behavior, category filters, maintenance aggregation, maintenance workspace routing, removal of implementation labels, Zones cleanup, and delivery selection handoff.

Browser QA covers vehicle creation with and without an image, vehicle detail health rendering, maintenance grouped and detail views, delivery selection to route planning, and desktop/narrow responsive layouts.

Regression checks cover backend tests and compilation, React build/lint/Vitest, existing route dispatch validation, and driver assignment consistency.

## Acceptance Criteria

- A permitted user can create a vehicle with or without a validated local image.
- Vehicle imagery appears in registry, detail, maintenance, and route vehicle-selection surfaces.
- Registration number remains the primary visible identifier.
- EV subsystem health is scan-friendly and does not use repetitive equal-size cards.
- Maintenance registry shows one row per vehicle and opens a vehicle-specific workspace.
- Existing maintenance create, complete, update, and cancel behavior remains functional.
- Delivery selection flows into route planning, and dispatch assigns one eligible driver and vehicle consistently to all linked orders.
- The selected Zones explanatory card and implementation-facing API labels are absent.
- Existing backend, predictive maintenance, demand, route, and mobile contracts remain compatible.
