import { Ban, Boxes, Eye, House, PackageOpen, Play, RefreshCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { OpenStreetMapPanel } from '../components/OpenStreetMapPanel'
import { Card, DataTable, ErrorState, LoadingState, OperationalInfo, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import { operationsService } from '../services/operationsService'
import { intelligenceService } from '../services/intelligenceService'
import { driverAdminService } from '../services/driverAdminService'
import type { AssignmentValidation, RoutePlan } from '../types'
import { consumeRouteDeliverySelection, consumeRoutePlanningContext } from '../features/deliveries/routeSelection'
import { buildOptimizationPayload } from '../features/routes/optimizationPayload'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'
import { LoadOptimizationPage } from './LoadOptimizationPage'
import { RouteSetDispatchWorkspace } from '../features/routes/RouteSetDispatchWorkspace'

export function RoutePlanningPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const workspace = searchParams.get('workspace') === 'dispatch' ? 'dispatch' : 'planning'
  const approvedPlanId = searchParams.get('plan') ?? ''
  const switchWorkspace = (next: 'planning' | 'dispatch', planId?: string) => {
    const updated = new URLSearchParams(searchParams)
    updated.set('workspace', next)
    if (planId) updated.set('plan', planId)
    setSearchParams(updated)
  }

  return <div>
    <div className="mb-5 inline-flex max-w-full rounded-lg border border-fleet-line bg-white p-1 shadow-sm" aria-label="Route and load workspace">
      <button className={`inline-flex min-h-10 items-center gap-2 rounded-md px-4 text-sm font-black ${workspace === 'planning' ? 'bg-fleet-blue text-white' : 'text-fleet-muted hover:bg-slate-50'}`} onClick={() => switchWorkspace('planning')} type="button"><Boxes className="h-4 w-4" />Planning candidates</button>
      <button className={`inline-flex min-h-10 items-center gap-2 rounded-md px-4 text-sm font-black ${workspace === 'dispatch' ? 'bg-fleet-blue text-white' : 'text-fleet-muted hover:bg-slate-50'}`} onClick={() => switchWorkspace('dispatch')} type="button"><PackageOpen className="h-4 w-4" />Route and dispatch</button>
    </div>
    {workspace === 'planning'
      ? <LoadOptimizationPage embedded onContinueToRoute={(planId) => switchWorkspace('dispatch', planId)} />
      : approvedPlanId ? <RouteSetDispatchWorkspace planId={approvedPlanId} /> : <DispatchRouteWorkspace />}
  </div>
}

function DispatchRouteWorkspace() {
  const currentUser = authService.getSession()
  const canOptimize = canAccess(currentUser, 'routes.optimize')
  const canDispatch = canAccess(currentUser, 'routes.dispatch')
  const [loadContext] = useState(() => consumeRoutePlanningContext())
  const [selectedVehicleId, setSelectedVehicleId] = useState(() => loadContext?.vehicleId ?? '')
  const [selectedDriverId, setSelectedDriverId] = useState('')
  const [validation, setValidation] = useState<AssignmentValidation | null>(null)
  const [actionError, setActionError] = useState('')
  const [activeRoute, setActiveRoute] = useState<RoutePlan | null>(null)
  const [deliveryOrderIds] = useState(() => consumeRouteDeliverySelection())
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [routePlan, routes, vehicles, modelStatus, drivers, branch] = await Promise.all([
      operationsService.getRoutePlan(),
      operationsService.listRoutes({ limit: 8 }),
      fleetService.listVehicles({ limit: 20 }),
      operationsService.getRouteModelStatus(),
      driverAdminService.listAssignable(),
      operationsService.getOperationalBranch(),
    ])
    return { routePlan, routes, vehicles, modelStatus, drivers, branch }
  }, [])

  const displayedRoute = activeRoute ?? data?.routePlan
  const routeVehicleId = data?.vehicles.some((vehicle) => vehicle.id === displayedRoute?.vehicle) ? displayedRoute?.vehicle ?? '' : ''
  const effectiveVehicleId = selectedVehicleId || routeVehicleId || ''

  useEffect(() => {
    if (!effectiveVehicleId || !displayedRoute?.id || displayedRoute.id === 'no-route') return
    intelligenceService.validateAssignment(effectiveVehicleId, displayedRoute.id).then(setValidation).catch(() => setValidation(null))
  }, [displayedRoute?.id, effectiveVehicleId])

  const recalculate = async () => {
    setActionError('')
    try {
      const optimized = await operationsService.optimizeRoute(buildOptimizationPayload({
        deliveryOrderIds,
        vehicleId: effectiveVehicleId,
        driverId: selectedDriverId,
        loadContext: loadContext ? { planId: loadContext.planId, loadId: loadContext.loadId } : null,
      }))
      setActiveRoute(optimized)
      setValidation(null)
      await reload()
    } catch (optimizationError) {
      setActionError(optimizationError instanceof Error ? optimizationError.message : 'Unable to optimize route')
    }
  }

  const dispatch = async () => {
    if (!displayedRoute?.id || displayedRoute.id === 'no-route') return
    setActionError('')
    try {
      const result = effectiveVehicleId ? await intelligenceService.validateAssignment(effectiveVehicleId, displayedRoute.id) : null
      setValidation(result)
      if (result && !result.eligible) return
      const dispatched = await operationsService.dispatchRoute(displayedRoute.id, { vehicle_id: effectiveVehicleId || undefined, driver_id: selectedDriverId || undefined })
      setActiveRoute(dispatched)
      await reload()
    } catch (dispatchError) {
      setActionError(dispatchError instanceof Error ? dispatchError.message : 'Unable to dispatch route')
    }
  }

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load route planning data'} onRetry={reload} />

  const routePlan = activeRoute ?? data.routePlan
  const modelAvailable = data.modelStatus.available === true
  const deliveryStops = routePlan.stops.filter((stop) => stop.status !== 'Origin' && stop.status !== 'Return')
  const routeMarkers = [{
    id: data.branch.id,
    kind: 'branch' as const,
    label: 'H',
    title: data.branch.name,
    subtitle: 'Fixed parcel origin and route return point',
    position: { latitude: data.branch.latitude, longitude: data.branch.longitude },
    color: '#047857',
  }, ...routePlan.stops
    .filter((stop) => stop.status !== 'Origin' && stop.status !== 'Return' && stop.latitude !== null && stop.longitude !== null)
    .map((stop) => ({
      id: `${stop.sequence}-${stop.name}`,
      label: String(stop.sequence),
      title: stop.name,
      subtitle: `${stop.eta} | ${stop.status}`,
      position: {
        latitude: stop.latitude as number,
        longitude: stop.longitude as number,
      },
      color: '#F59E0B',
    }))]

  return (
    <div>
      <PageHeader
        action={canDispatch ? <PrimaryButton disabled={routePlan.id === 'no-route' || validation?.eligible === false || !effectiveVehicleId || !selectedDriverId} onClick={dispatch}><Play className="h-4 w-4" /> Dispatch Route</PrimaryButton> : undefined}
        description="Build one delivery-date and half-day parcel batch from the fixed Colombo branch origin."
        title="Dispatch Configuration"
      />
      <div className="mb-5 flex items-center gap-2">
        <StatusBadge tone={routePlan.id === 'no-route' ? 'slate' : modelAvailable ? 'green' : 'amber'}>{routePlan.id === 'no-route' ? 'Not Optimized' : modelAvailable ? 'Predictive ETA Active' : 'Distance Fallback'}</StatusBadge>
        <OperationalInfo severity={modelAvailable ? 'info' : 'warning'} title="Route cost method">{routePlan.warning || (modelAvailable ? 'Expected travel time, weather, and delay conditions contribute to the route sequence.' : 'Distance-based cost is used while predictive ETA is unavailable.')}{routePlan.weatherWarnings?.length ? ` ${routePlan.weatherWarnings.join(' ')}` : ''}</OperationalInfo>
        <StatusBadge tone={routePlan.weatherAvailable ? 'blue' : 'slate'}>{routePlan.weatherAvailable ? 'Live Weather' : 'Weather Default'}</StatusBadge>
        {routePlan.id !== 'no-route' && <StatusBadge tone={routePlan.geometrySource === 'osrm' ? 'green' : 'amber'}>{routePlan.geometrySource === 'osrm' ? 'Road Geometry' : 'Straight-line Fallback'}</StatusBadge>}
        {deliveryOrderIds.length > 0 && <StatusBadge tone="blue">{deliveryOrderIds.length} selected parcels</StatusBadge>}
        {routePlan.deliveryDate && <StatusBadge tone="slate">{routePlan.deliveryDate}</StatusBadge>}
        {routePlan.deliveryPeriod && <StatusBadge tone="blue">{routePlan.deliveryPeriod === 'first_half' ? 'First Half · 08:00–12:00' : 'Second Half · 13:00–17:00'}</StatusBadge>}
      </div>
      <Card className="mb-5" title="Saved route plans">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {data.routes.map((route) => <div className="flex min-w-0 items-center justify-between gap-2 rounded-lg border border-fleet-line p-3" key={route.id}><div className="min-w-0"><div className="truncate text-sm font-black">{route.routeCode || route.id}</div><div className="text-xs font-semibold text-fleet-muted">{route.deliveryDate || 'Unscheduled'} · {route.status || 'optimized'}</div></div><div className="flex gap-1"><button aria-label="View route" className="rounded-lg p-2 hover:bg-blue-50 hover:text-fleet-blue" onClick={() => operationsService.getRoutePlan(route.id).then(setActiveRoute).catch(() => setActionError('Unable to open saved route'))} title="View route" type="button"><Eye className="h-4 w-4" /></button>{canOptimize && route.status === 'optimized' && <button aria-label="Cancel route" className="rounded-lg p-2 hover:bg-red-50 hover:text-red-700" onClick={async () => { if (!window.confirm('Cancel this optimized route and release its parcels?')) return; try { const cancelled = await operationsService.cancelRoute(route.id); if (routePlan.id === route.id) setActiveRoute(cancelled); await reload() } catch (reason) { setActionError(reason instanceof Error ? reason.message : 'Unable to cancel route') } }} title="Cancel route" type="button"><Ban className="h-4 w-4" /></button>}</div></div>)}
        </div>
      </Card>
      {deliveryOrderIds.length === 0 && (
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-900">
          <span>Select pending parcels before choosing a vehicle and driver for optimization.</span>
          <Link className="rounded-lg bg-white px-3 py-2 font-bold text-amber-900 ring-1 ring-amber-300 hover:bg-amber-100" to="/deliveries">Open Parcel Gallery</Link>
        </div>
      )}
      {(actionError || validation?.blockingReasons.length) ? <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{actionError || validation?.blockingReasons.join('; ')}</div> : validation?.warnings.length ? <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">{validation.warnings.join('; ')}</div> : null}
      <div className="grid min-w-0 gap-5 xl:grid-cols-[430px_1fr]">
        <div className="min-w-0 space-y-5">
          <Card title="Configuration">
            <div className="flex items-start gap-3 rounded-lg border border-emerald-200 bg-emerald-50 p-3"><span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-emerald-700 text-white"><House className="h-4 w-4" /></span><div><div className="text-xs font-bold uppercase text-emerald-700">Fixed route origin</div><div className="font-black text-emerald-950">{data.branch.name}</div><div className="text-xs font-semibold text-emerald-800">{data.branch.address}</div></div></div>
            <label className="mt-4 block text-sm font-bold text-fleet-muted">Assigned Vehicle<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold" onChange={(event) => setSelectedVehicleId(event.target.value)} value={effectiveVehicleId}><option value="">Select a vehicle</option>{data.vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.registrationNumber} · {vehicle.category} · {vehicle.risk} risk</option>)}</select></label>
            <label className="mt-4 block text-sm font-bold text-fleet-muted">Assigned Driver<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold" onChange={(event) => setSelectedDriverId(event.target.value)} value={selectedDriverId}><option value="">Select an enrolled driver</option>{data.drivers.map((driver) => <option key={driver.id} value={driver.id}>@{driver.username} · {driver.full_name}</option>)}</select></label>
            <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs font-medium leading-5 text-fleet-muted">Choose an enrolled driver and an eligible vehicle. Optimization links the selected parcels; dispatch assigns that route and its deliveries to both.</p>
          </Card>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Stat label="Total Cost" value={routePlan.distance} />
            <Stat label="Estimated ETA" value={routePlan.eta} />
            <Stat label="Capacity Use" value={`${routePlan.capacityUse}%`} progress={routePlan.capacityUse} />
            <Stat label="Delivery Stops" value={`${deliveryStops.length}`} />
          </div>
        </div>
        <div className="min-w-0">
        <Card action={canOptimize ? <SecondaryButton disabled={!effectiveVehicleId || !selectedDriverId || deliveryOrderIds.length === 0} onClick={recalculate}><RefreshCcw className="h-4 w-4" /> Optimize Selected</SecondaryButton> : undefined} title="Optimized Route Path">
          <OpenStreetMapPanel
            className="mb-4 min-h-[300px]"
            markers={routeMarkers}
            polylines={routePlan.mapPath.length > 1 ? [{ id: routePlan.id, path: routePlan.mapPath, color: '#1D4ED8' }] : []}
          />
          <DataTable headers={['Seq', 'Location / Entity', 'Est. Arrival', 'Load Drop', 'Status']}>
            {routePlan.stops.map((stop) => (
              <tr key={`${stop.sequence}-${stop.name}`}>
                <td className="px-5 py-4 font-black">{String(stop.sequence).padStart(2, '0')}</td>
                <td className="px-5 py-4 font-black text-fleet-blue">{stop.name}</td>
                <td className="px-5 py-4">{stop.eta}</td>
                <td className="px-5 py-4">{stop.loadDrop}</td>
                <td className="px-5 py-4"><StatusBadge tone={stop.status === 'Origin' ? 'green' : 'slate'}>{stop.status}</StatusBadge></td>
              </tr>
            ))}
          </DataTable>
        </Card>
        </div>
      </div>
    </div>
  )
}

function Stat({ label, value, progress }: { label: string; value: string; progress?: number }) {
  return <div className="rounded-2xl border border-fleet-line bg-white p-5 shadow-card"><div className="text-sm font-bold text-fleet-muted">{label}</div><div className="mt-2 text-2xl font-black">{value}</div>{progress !== undefined && <div className="mt-3 h-2 rounded-full bg-slate-100"><div className="h-full rounded-full bg-fleet-blue" style={{ width: `${progress}%` }} /></div>}</div>
}
