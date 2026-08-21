# Vehicle and Maintenance Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add secure local vehicle images and deliver a registration-first vehicle health, maintenance fleet, and route-assignment experience without breaking existing APIs or driver workflows.

**Architecture:** FastAPI stores validated vehicle media under a managed local directory and exposes an optional `image_url` through existing vehicle contracts. React adapts that field once, reuses focused vehicle-media and subsystem components, and aggregates existing vehicle/maintenance/part data into vehicle-centered views; route dispatch remains the sole authoritative multi-order assignment operation.

**Tech Stack:** FastAPI, Motor/MongoDB, `python-multipart`, React 19, TypeScript, Vite, Tailwind CSS, Lucide React, React Router, Vitest.

## Global Constraints

- Store vehicle media only under `backend/media/vehicles/`; MongoDB stores a nullable public `image_url`.
- Accept JPEG, PNG, and WebP only, with a maximum file size of 5 MB.
- Server-generated filenames must prevent path traversal and collisions.
- Registration number is the primary visible vehicle identifier; vehicle code remains secondary.
- Existing vehicles without images and existing JSON vehicle create/update requests remain valid.
- Existing predictive, maintenance, demand, route, delivery, and driver-mobile contracts must remain compatible.
- Route dispatch assigns one eligible vehicle and one enrolled driver consistently to all linked delivery orders.
- Remove implementation-facing labels, but retain actionable errors, live connectivity state, model fallback state, and safety warnings.
- Use existing Tailwind tokens and Lucide icons; respect `prefers-reduced-motion`.

---

### Task 1: Secure Vehicle Media Backend

**Files:**
- Create: `backend/app/services/vehicle_media_service.py`
- Create: `backend/tests/test_vehicle_media.py`
- Modify: `backend/requirements.txt`
- Modify: `backend/app/models/vehicle_model.py`
- Modify: `backend/app/schemas/vehicle_schema.py`
- Modify: `backend/app/routes/vehicle_routes.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `save_vehicle_image(vehicle_id: str, upload: UploadFile) -> dict[str, Any]`
- Produces: `delete_vehicle_image(vehicle_id: str) -> dict[str, Any]`
- Produces: `POST /api/vehicles/{vehicle_id}/image` and `DELETE /api/vehicles/{vehicle_id}/image`
- Produces: optional `image_url: str | None` in all vehicle responses.

- [ ] **Step 1: Add failing media validation and schema tests**

```python
from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, UploadFile

from app.schemas.vehicle_schema import VehicleResponse
from app.services.vehicle_media_service import validate_vehicle_image


def test_existing_vehicle_response_accepts_missing_image_url():
    payload = {
        "id": "507f1f77bcf86cd799439011",
        "vehicle_code": "EV-001",
        "registration_number": "WP CAA-1201",
        "vehicle_type": "electric_van",
        "brand": "BYD",
        "model": "T3",
        "year": 2026,
        "fuel_type": "electric",
        "current_mileage": 1200,
        "status": "active",
        "health_status": "healthy",
        "created_at": "2026-08-16T00:00:00Z",
        "updated_at": "2026-08-16T00:00:00Z",
    }
    result = VehicleResponse.model_validate(payload)
    assert result.image_url is None


@pytest.mark.asyncio
async def test_rejects_oversized_vehicle_image():
    upload = UploadFile(filename="van.png", file=BytesIO(b"x" * (5 * 1024 * 1024 + 1)), headers={"content-type": "image/png"})
    with pytest.raises(HTTPException) as exc:
        await validate_vehicle_image(upload)
    assert exc.value.status_code == 413


@pytest.mark.asyncio
async def test_rejects_unsupported_vehicle_image():
    upload = UploadFile(filename="van.svg", file=BytesIO(b"<svg/>"), headers={"content-type": "image/svg+xml"})
    with pytest.raises(HTTPException) as exc:
        await validate_vehicle_image(upload)
    assert exc.value.status_code == 415
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run: `python -m pytest tests/test_vehicle_media.py -q`

Expected: FAIL because `vehicle_media_service` and `image_url` do not exist.

- [ ] **Step 3: Add multipart dependency and optional vehicle field**

Add `python-multipart` to `backend/requirements.txt`. Add `image_url: str | None = None` to `VehicleCreate`, `VehicleUpdate`, and `VehicleResponse`; add `"image_url": data.get("image_url")` to `build_vehicle_document()`.

- [ ] **Step 4: Implement confined file validation and persistence**

```python
MEDIA_ROOT = Path(__file__).resolve().parents[2] / "media"
VEHICLE_MEDIA_ROOT = MEDIA_ROOT / "vehicles"
MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def validate_vehicle_image(upload: UploadFile) -> tuple[bytes, str]:
    suffix = ALLOWED_IMAGE_TYPES.get(upload.content_type or "")
    if suffix is None:
        raise HTTPException(status_code=415, detail="Vehicle image must be JPEG, PNG, or WebP")
    content = await upload.read(MAX_IMAGE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=400, detail="Vehicle image is empty")
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Vehicle image must not exceed 5 MB")
    return content, suffix
```

`save_vehicle_image()` validates the vehicle ObjectId and existence, writes `<uuid4><suffix>` beneath the resolved media root, updates `image_url` to `/media/vehicles/<name>`, and removes the previous managed file after the database update succeeds. `delete_vehicle_image()` sets `image_url=None` and safely removes only a path whose resolved parent is `VEHICLE_MEDIA_ROOT`.

- [ ] **Step 5: Register routes and static media**

```python
@router.post("/{vehicle_id}/image")
async def upload_vehicle_image(
    vehicle_id: str,
    image: UploadFile = File(...),
    _: dict = Depends(require_roles(["admin", "fleet_manager"])),
) -> dict:
    return success_response("Vehicle image uploaded successfully", data=await save_vehicle_image(vehicle_id, image))
```

Mount `StaticFiles(directory=MEDIA_ROOT, check_dir=False)` at `/media` in `app/main.py` after creating the directory. Add the DELETE route with the same roles.

- [ ] **Step 6: Run backend tests and commit**

Run:

```powershell
python -m pytest tests/test_vehicle_media.py -q
python -m pytest tests -q
python -m compileall app
```

Expected: all pass.

Commit:

```bash
git add backend/requirements.txt backend/app/main.py backend/app/models/vehicle_model.py backend/app/schemas/vehicle_schema.py backend/app/routes/vehicle_routes.py backend/app/services/vehicle_media_service.py backend/tests/test_vehicle_media.py
git commit -m "feat: add secure vehicle image uploads"
```

### Task 2: Frontend Media Contract and Reusable Vehicle Identity

**Files:**
- Create: `Fleet_Web_App/frontend/src/components/VehicleIdentity.tsx`
- Create: `Fleet_Web_App/frontend/src/services/vehiclePresentation.test.ts`
- Modify: `Fleet_Web_App/frontend/src/services/apiClient.ts`
- Modify: `Fleet_Web_App/frontend/src/services/adapters.ts`
- Modify: `Fleet_Web_App/frontend/src/services/fleetService.ts`
- Modify: `Fleet_Web_App/frontend/src/types.ts`

**Interfaces:**
- Consumes: backend `image_url` and upload routes from Task 1.
- Produces: `apiClient.upload<T>(path: string, formData: FormData): Promise<T>`.
- Produces: `fleetService.uploadVehicleImage(vehicleId: string, image: File): Promise<Vehicle>`.
- Produces: `Vehicle.imageUrl: string | null`.
- Produces: `<VehicleIdentity vehicle size="sm|md|lg" />`.

- [ ] **Step 1: Add failing adapter and upload request tests**

```typescript
it('maps an API vehicle image to an absolute media URL', () => {
  const vehicle = mapVehicle({ id: 'v1', registration_number: 'WP CAA-1201', image_url: '/media/vehicles/v1.webp' })
  expect(vehicle.imageUrl).toBe('http://127.0.0.1:8000/media/vehicles/v1.webp')
})

it('sends FormData without forcing application/json', async () => {
  const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ success: true, message: 'ok', data: {} }), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  }))
  const form = new FormData()
  form.append('image', new File(['image'], 'ev.webp', { type: 'image/webp' }))
  await apiClient.upload('/vehicles/v1/image', form)
  const headers = new Headers(fetchMock.mock.calls[0][1]?.headers)
  expect(headers.has('Content-Type')).toBe(false)
})
```

- [ ] **Step 2: Run focused frontend tests and confirm failure**

Run: `npm.cmd run test -- vehiclePresentation.test.ts`

Expected: FAIL because `imageUrl` and `upload()` do not exist.

- [ ] **Step 3: Add multipart-aware API client**

Change request serialization to preserve `FormData`:

```typescript
const isFormData = body instanceof FormData
if (body !== undefined && !isFormData && !requestHeaders.has('Content-Type')) {
  requestHeaders.set('Content-Type', 'application/json')
}
body: body === undefined ? undefined : isFormData ? body : JSON.stringify(body)
```

Expose `upload<T>(path, formData)` as POST using the shared authentication/error path.

- [ ] **Step 4: Add vehicle media mapping and service calls**

Add `imageUrl: string | null` to `Vehicle`. Implement a `mediaUrl()` helper using the API origin (remove trailing `/api`) and preserve full HTTP URLs. Map `image_url`, implement upload/delete service calls, and return `mapVehicle(data)`.

- [ ] **Step 5: Build the reusable identity component**

`VehicleIdentity` renders a stable-aspect image with `object-cover`, an EV fallback containing `Truck` icon, registration as primary text, and code/category as secondary text. Sizes use fixed responsive constraints so missing images do not shift rows.

- [ ] **Step 6: Run tests/build and commit**

Run:

```powershell
npm.cmd run test
npm.cmd run build
```

Commit:

```bash
git add Fleet_Web_App/frontend/src/components/VehicleIdentity.tsx Fleet_Web_App/frontend/src/services/apiClient.ts Fleet_Web_App/frontend/src/services/adapters.ts Fleet_Web_App/frontend/src/services/fleetService.ts Fleet_Web_App/frontend/src/services/vehiclePresentation.test.ts Fleet_Web_App/frontend/src/types.ts
git commit -m "feat: add vehicle media frontend contract"
```

### Task 3: Vehicle Registry and Creation Experience

**Files:**
- Create: `Fleet_Web_App/frontend/src/components/VehicleForm.tsx`
- Create: `Fleet_Web_App/frontend/src/components/VehicleForm.test.tsx`
- Modify: `Fleet_Web_App/frontend/src/pages/VehiclesPage.tsx`

**Interfaces:**
- Consumes: `fleetService.createVehicle()`, `fleetService.uploadVehicleImage()`, and `VehicleIdentity`.
- Produces: `<VehicleForm onCreated={(vehicle) => void} onCancel={() => void} />`.

- [ ] **Step 1: Write failing form workflow tests**

Test that the form previews a selected image, provides Identity/EV Specifications/Operational State sections, does not show `Backend API`, rejects a file over 5 MB client-side, creates the vehicle first, uploads the optional image using the returned ID, and exposes a retry message when image upload fails after vehicle creation.

```typescript
expect(screen.getByRole('heading', { name: 'Vehicle identity' })).toBeInTheDocument()
expect(screen.queryByText(/Backend API/i)).not.toBeInTheDocument()
expect(fleetService.createVehicle).toHaveBeenCalledBefore(fleetService.uploadVehicleImage)
```

- [ ] **Step 2: Run test and confirm failure**

Run: `npm.cmd run test -- VehicleForm.test.tsx`

Expected: FAIL because `VehicleForm` does not exist.

- [ ] **Step 3: Implement sectioned creation form**

Use one modal/dialog surface with an image drop area and three unframed field groups. Fuel type is displayed as Electric and submitted as `electric`. Status defaults to active and health to unknown. Driver assignment is absent. Use dropdowns for vehicle category, operational status, and health status; keep registration placeholder `WP CAA-1234`.

- [ ] **Step 4: Modernize the vehicle registry without changing density**

Keep the scan-friendly table. Replace the first cell with `VehicleIdentity size="sm"`, make risk/status/category filters functional, and remove implementation labels and duplicate action/risk columns. Use a clear View action with `ChevronRight` or make the row keyboard-navigable.

- [ ] **Step 5: Run tests and responsive browser check**

Run:

```powershell
npm.cmd run test -- VehicleForm.test.tsx
npm.cmd run build
```

Browser check `/vehicles` at 1440x900 and 390x844: no clipped dialog, image preview stable, longest registration fits, keyboard focus visible.

- [ ] **Step 6: Commit**

```bash
git add Fleet_Web_App/frontend/src/components/VehicleForm.tsx Fleet_Web_App/frontend/src/components/VehicleForm.test.tsx Fleet_Web_App/frontend/src/pages/VehiclesPage.tsx
git commit -m "feat: modernize vehicle registry and creation"
```

### Task 4: EV Subsystem Health Detail

**Files:**
- Create: `Fleet_Web_App/frontend/src/components/VehicleSubsystemList.tsx`
- Create: `Fleet_Web_App/frontend/src/components/VehicleSubsystemList.test.tsx`
- Modify: `Fleet_Web_App/frontend/src/pages/VehicleDetailPage.tsx`
- Modify: `Fleet_Web_App/frontend/src/services/fleetService.ts`

**Interfaces:**
- Consumes: `Vehicle`, `VehiclePart`, maintenance records, and `VehicleIdentity`.
- Produces: `<VehicleSubsystemList parts onSelectPart />` and selected-part detail state.

- [ ] **Step 1: Add failing subsystem semantics tests**

```typescript
render(<VehicleSubsystemList parts={parts} onSelectPart={vi.fn()} />)
expect(screen.getByText('Battery Pack')).toBeInTheDocument()
expect(screen.getByLabelText('Battery Pack risk score 62 percent')).toBeInTheDocument()
expect(screen.getByTestId('subsystem-battery-pack')).toHaveClass('border-amber-200')
```

Also verify Battery, Snowflake, Gauge, CircleGauge, Disc3, CircleDot, PlugZap, and Thermometer icons are selected through an explicit part-name mapping with a Wrench fallback.

- [ ] **Step 2: Run test and confirm failure**

Run: `npm.cmd run test -- VehicleSubsystemList.test.tsx`

- [ ] **Step 3: Preserve numeric risk score in adapters**

Add `riskScore: number` and `status: string` to `VehiclePart`. Map `risk_score` and backend part status without changing the existing derived `risk` field.

- [ ] **Step 4: Implement structured subsystem rows**

Use stable grid columns for icon/name, status, risk bar, last service, next maintenance, and chevron action. Use semantic color only for risk/status and subtle pulse only for high/critical with `motion-reduce:animate-none`.

- [ ] **Step 5: Redesign detail composition**

Add a top vehicle identity band with image. Create four compact summary cells for health, predictive risk, open maintenance, and next service. Place subsystem list at two-thirds width and maintenance timeline at one-third on desktop; stack on narrow screens. Remove `Backend API` and seed-note labels from visible chrome while retaining meaningful notes in detail text where necessary.

- [ ] **Step 6: Run tests/build and commit**

```powershell
npm.cmd run test -- VehicleSubsystemList.test.tsx
npm.cmd run test
npm.cmd run build
```

```bash
git add Fleet_Web_App/frontend/src/components/VehicleSubsystemList.tsx Fleet_Web_App/frontend/src/components/VehicleSubsystemList.test.tsx Fleet_Web_App/frontend/src/pages/VehicleDetailPage.tsx Fleet_Web_App/frontend/src/services/fleetService.ts Fleet_Web_App/frontend/src/types.ts
git commit -m "feat: redesign EV subsystem health view"
```

### Task 5: Vehicle-Centered Maintenance Registry and Workspace

**Files:**
- Create: `Fleet_Web_App/frontend/src/features/maintenance/maintenanceSummary.ts`
- Create: `Fleet_Web_App/frontend/src/features/maintenance/maintenanceSummary.test.ts`
- Create: `Fleet_Web_App/frontend/src/pages/VehicleMaintenancePage.tsx`
- Create: `Fleet_Web_App/frontend/src/pages/VehicleMaintenancePage.test.tsx`
- Modify: `Fleet_Web_App/frontend/src/pages/MaintenancePage.tsx`
- Modify: `Fleet_Web_App/frontend/src/App.tsx`
- Modify: `Fleet_Web_App/frontend/src/types.ts`

**Interfaces:**
- Consumes: `Vehicle[]`, `MaintenanceRecord[]`, and per-vehicle `VehiclePart[]`.
- Produces: `buildVehicleMaintenanceSummaries(vehicles, records, now): VehicleMaintenanceSummary[]`.
- Produces: `/maintenance/vehicle/:vehicleId` route.

- [ ] **Step 1: Write failing aggregation tests**

```typescript
const summary = buildVehicleMaintenanceSummaries([vehicle], records, new Date('2026-08-20T00:00:00Z'))[0]
expect(summary.totalRecords).toBe(3)
expect(summary.openWork).toBe(2)
expect(summary.overdue).toBe(1)
expect(summary.criticalWork).toBe(1)
expect(summary.outstandingCost).toBe(12000)
```

Define completed as `Completed`; open work is every other status; overdue is explicit `Overdue` or a non-completed service date before `now`; critical work uses preserved backend priority. Therefore extend `MaintenanceRecord` and `mapMaintenanceRecord()` with `vehicleId`, `partName`, `maintenanceType`, `priority`, `rawStatus`, and numeric `costValue`.

- [ ] **Step 2: Run aggregation test and confirm failure**

Run: `npm.cmd run test -- maintenanceSummary.test.ts`

- [ ] **Step 3: Implement pure aggregation**

Return one summary for every vehicle, including vehicles with zero records. Sort by blocked/critical, overdue count, open work, then registration number. Do not fetch parts for all vehicles on the registry page; pending-part counts are derived from maintenance status there and exact part risk is loaded in the detail workspace.

- [ ] **Step 4: Replace maintenance record table with vehicle rows**

Use `VehicleIdentity`, health/status badges, total/open/overdue/critical metrics, last service, next due, and outstanding cost. Implement search, category, health, state, and overdue filters. Row click and keyboard Enter navigate to `/maintenance/vehicle/<id>`.

- [ ] **Step 5: Build failing workspace tests**

Mock `getVehicle`, `listVehicleParts`, `listMaintenanceRecords({vehicle_id})`, and predictions. Verify the page displays only the selected vehicle, separates Open Work and Completed History, and complete action reloads the workspace.

- [ ] **Step 6: Implement the maintenance workspace and route**

Reuse the vehicle identity and subsystem list. Keep the existing maintenance form behavior but preselect and lock the current vehicle. Add Back to Maintenance Fleet and View Full Vehicle links. Register:

```tsx
<Route
  element={<PermissionRoute permission="maintenance.view"><VehicleMaintenancePage /></PermissionRoute>}
  path="/maintenance/vehicle/:vehicleId"
/>
```

- [ ] **Step 7: Run tests/build and commit**

```powershell
npm.cmd run test -- maintenanceSummary.test.ts VehicleMaintenancePage.test.tsx
npm.cmd run test
npm.cmd run build
```

```bash
git add Fleet_Web_App/frontend/src/features/maintenance Fleet_Web_App/frontend/src/pages/MaintenancePage.tsx Fleet_Web_App/frontend/src/pages/VehicleMaintenancePage.tsx Fleet_Web_App/frontend/src/pages/VehicleMaintenancePage.test.tsx Fleet_Web_App/frontend/src/App.tsx Fleet_Web_App/frontend/src/types.ts Fleet_Web_App/frontend/src/services/adapters.ts
git commit -m "feat: add vehicle-centered maintenance workspace"
```

### Task 6: Delivery Handoff, Zones Cleanup, and Operational Copy Audit

**Files:**
- Create: `Fleet_Web_App/frontend/src/utils/selectedDeliveries.ts`
- Create: `Fleet_Web_App/frontend/src/utils/selectedDeliveries.test.ts`
- Modify: `Fleet_Web_App/frontend/src/pages/DeliveriesPage.tsx`
- Modify: `Fleet_Web_App/frontend/src/pages/RoutePlanningPage.tsx`
- Modify: `Fleet_Web_App/frontend/src/pages/ZonesPage.tsx`
- Modify: operational page files returned by the copy audit.

**Interfaces:**
- Produces: `saveSelectedDeliveryIds(ids: string[]): void` and `consumeSelectedDeliveryIds(): string[]` using session storage key `fleetopt:selected-delivery-ids`.
- Consumes: existing route optimize/dispatch request with `delivery_order_ids`, `vehicle_id`, and `driver_id`.

- [ ] **Step 1: Write failing handoff tests**

```typescript
saveSelectedDeliveryIds(['order-1', 'order-2'])
expect(consumeSelectedDeliveryIds()).toEqual(['order-1', 'order-2'])
expect(consumeSelectedDeliveryIds()).toEqual([])
```

Add a Deliveries page test that selecting pending orders and clicking `Plan selected deliveries` saves IDs and navigates to `/route-planning`.

- [ ] **Step 2: Run tests and confirm failure**

Run: `npm.cmd run test -- selectedDeliveries.test.ts`

- [ ] **Step 3: Implement one-time delivery handoff**

Persist only order IDs, never parcel/customer details. Route Planning consumes IDs once, preselects matching pending orders, and still requires explicit eligible vehicle and enrolled driver selection before optimization/dispatch. It sends the final IDs, vehicle ID, and driver ID to existing backend calls.

- [ ] **Step 4: Remove the selected Zones card**

Remove the `Planning Signal` section and its explanatory text. Keep selected-zone metrics, forecast/actual/calibration information, refresh/import action, and operational warnings.

- [ ] **Step 5: Remove implementation-facing copy globally**

Run:

```powershell
rg -n "Backend API|Backend live|History API|Route API|Creates a backend|Schedules backend" Fleet_Web_App/frontend/src
```

Replace each match with user-centered status/copy or remove it. Do not remove `Model loaded`, `Distance fallback`, connectivity errors, calibration state, or safety warnings.

- [ ] **Step 6: Run tests/build and commit**

```powershell
npm.cmd run test
npm.cmd run lint
npm.cmd run build
```

```bash
git add Fleet_Web_App/frontend/src/utils/selectedDeliveries.ts Fleet_Web_App/frontend/src/utils/selectedDeliveries.test.ts Fleet_Web_App/frontend/src/pages/DeliveriesPage.tsx Fleet_Web_App/frontend/src/pages/RoutePlanningPage.tsx Fleet_Web_App/frontend/src/pages/ZonesPage.tsx
git commit -m "feat: connect delivery selection to route planning"
```

### Task 7: End-to-End Verification and Documentation

**Files:**
- Modify: `backend/README.md`
- Modify: `setup.md`

**Interfaces:**
- Consumes all completed tasks.
- Produces verified operational workflow and setup documentation.

- [ ] **Step 1: Install compatible dependencies**

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Confirm `python-multipart` imports under the same Python 3.10 environment used by Uvicorn.

- [ ] **Step 2: Run backend verification**

```powershell
.\.venv\Scripts\python.exe -m compileall app scripts
python -m pytest tests -q
.\.venv\Scripts\python.exe -c "from app.main import app; print(app.title); print(len(app.routes))"
```

Expected: compilation and all tests pass; media mount and image routes appear without startup failure.

- [ ] **Step 3: Run frontend verification**

```powershell
cd Fleet_Web_App/frontend
npm.cmd run test
npm.cmd run lint
npm.cmd run build
```

Expected: all pass.

- [ ] **Step 4: Run manual browser workflow**

Start backend and web app. As admin:

1. Create an EV with a WebP/JPEG image.
2. Confirm image on Vehicle Registry and Vehicle Detail.
3. Confirm EV subsystem list, risk bars, and maintenance timeline.
4. Open Maintenance and verify one row per vehicle.
5. Open the new vehicle maintenance workspace and complete one scheduled record.
6. Select two unassigned deliveries and open Route Planning.
7. Confirm the same orders are selected, choose an eligible vehicle and enrolled driver, optimize, and dispatch.
8. Confirm linked orders carry the final driver/vehicle assignment.
9. Confirm Zones has no Planning Signal card.
10. Confirm no implementation-facing API labels remain.

- [ ] **Step 5: Responsive and visual QA**

Capture Vehicle Registry, Add Vehicle, Vehicle Detail, Maintenance Registry, Maintenance Workspace, Deliveries, Route Planning, and Zones at 1440x900 and 390x844. Check text fit, stable image dimensions, modal scroll, table overflow behavior, icon alignment, keyboard focus, semantic colors, and reduced-motion behavior. Use `view_image` to inspect screenshots before completion.

- [ ] **Step 6: Document and commit**

Document local media storage, upload limits, backup/deployment warning, and route-based assignment flow. State that production deployments should replace local media with durable object storage.

```bash
git add backend/README.md setup.md
git commit -m "docs: explain vehicle media and maintenance workflow"
```

- [ ] **Step 7: Final integrity checks**

```powershell
git diff --check
git status --short
```

Confirm no uploaded test image, `.env`, credential, token, local database file, or generated QA screenshot is staged.
