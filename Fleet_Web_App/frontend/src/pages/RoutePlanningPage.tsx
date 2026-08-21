import { Play, RefreshCcw } from 'lucide-react'
import { useEffect, useState } from 'react'
import { GoogleMapPanel } from '../components/GoogleMapPanel'
import { Card, DataTable, ErrorState, LoadingState, OperationalInfo, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import { operationsService } from '../services/operationsService'
import { intelligenceService } from '../services/intelligenceService'
import { driverAdminService } from '../services/driverAdminService'
import type { AssignmentValidation } from '../types'
import { consumeRouteDeliverySelection } from '../features/deliveries/routeSelection'

export function RoutePlanningPage() {
  const [selectedVehicleId, setSelectedVehicleId] = useState('')
  const [selectedDriverId, setSelectedDriverId] = useState('')
  const [validation, setValidation] = useState<AssignmentValidation | null>(null)
  const [actionError, setActionError] = useState('')
  const [deliveryOrderIds] = useState(() => consumeRouteDeliverySelection())
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [routePlan, vehicles, modelStatus, drivers] = await Promise.all([
      operationsService.getRoutePlan(),
      fleetService.listVehicles({ limit: 20 }),
      operationsService.getRouteModelStatus(),
      driverAdminService.listAssignable(),
    ])
    return { routePlan, vehicles, modelStatus, drivers }
  }, [])

  const routeVehicleId = data?.vehicles.some((vehicle) => vehicle.id === data.routePlan.vehicle) ? data.routePlan.vehicle : ''
  const effectiveVehicleId = selectedVehicleId || routeVehicleId || ''

  useEffect(() => {
    if (!effectiveVehicleId || !data?.routePlan.id || data.routePlan.id === 'no-route') return
    intelligenceService.validateAssignment(effectiveVehicleId, data.routePlan.id).then(setValidation).catch(() => setValidation(null))
  }, [data?.routePlan.id, effectiveVehicleId])

  const recalculate = async () => {
    const stops = [
      { order_code: 'WEB-STOP-1', drop_latitude: 6.8649, drop_longitude: 79.8997, zone_id: 'LK_nugegoda', priority: 'medium' },
      { order_code: 'WEB-STOP-2', drop_latitude: 6.9061, drop_longitude: 79.9696, zone_id: 'LK_malabe', priority: 'high' },
    ]
    await operationsService.optimizeRoute({
      depot_latitude: 6.9271,
      depot_longitude: 79.8612,
      depot_name: 'Colombo Depot',
      vehicle_id: effectiveVehicleId || undefined,
      driver_id: selectedDriverId || undefined,
      ...(deliveryOrderIds.length ? { delivery_order_ids: deliveryOrderIds } : { delivery_stops: stops }),
      use_ml_cost: true,
      include_demand_context: true,
      include_maintenance_context: true,
      include_weather_context: true,
      save_route: true,
    })
    await reload()
  }

  const dispatch = async () => {
    if (!data?.routePlan.id || data.routePlan.id === 'no-route') return
    setActionError('')
    try {
      const result = effectiveVehicleId ? await intelligenceService.validateAssignment(effectiveVehicleId, data.routePlan.id) : null
      setValidation(result)
      if (result && !result.eligible) return
      await operationsService.dispatchRoute(data.routePlan.id, { vehicle_id: effectiveVehicleId || undefined, driver_id: selectedDriverId || undefined })
      await reload()
    } catch (dispatchError) {
      setActionError(dispatchError instanceof Error ? dispatchError.message : 'Unable to dispatch route')
    }
  }

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load route planning data'} onRetry={reload} />

  const { routePlan } = data
  const modelAvailable = data.modelStatus.available === true
  const routeMarkers = routePlan.stops
    .filter((stop) => stop.latitude !== null && stop.longitude !== null)
    .map((stop) => ({
      id: `${stop.sequence}-${stop.name}`,
      label: stop.status === 'Origin' ? 'D' : String(stop.sequence),
      title: stop.name,
      subtitle: `${stop.eta} | ${stop.status}`,
      position: {
        latitude: stop.latitude as number,
        longitude: stop.longitude as number,
      },
      color: stop.status === 'Origin' ? '#1D4ED8' : '#F59E0B',
    }))

  return (
    <div>
      <PageHeader
        action={<PrimaryButton disabled={routePlan.id === 'no-route' || validation?.eligible === false || !effectiveVehicleId || !selectedDriverId} onClick={dispatch}><Play className="h-4 w-4" /> Dispatch Route</PrimaryButton>}
        description="Configure and optimize routes before finalizing dispatch orders."
        title="Dispatch Configuration"
      />
      <div className="mb-5 flex items-center gap-2">
        <StatusBadge tone={routePlan.id === 'no-route' ? 'slate' : modelAvailable ? 'green' : 'amber'}>{routePlan.id === 'no-route' ? 'Not Optimized' : modelAvailable ? 'ML Cost Active' : 'Distance Fallback'}</StatusBadge>
        <OperationalInfo severity={modelAvailable ? 'info' : 'warning'} title="Route cost method">{routePlan.warning || (modelAvailable ? 'ETA, live weather context, and delay probability contribute to the OR-Tools route cost.' : 'Distance-based cost is used while the ML artifact is unavailable.')}{routePlan.weatherWarnings?.length ? ` ${routePlan.weatherWarnings.join(' ')}` : ''}</OperationalInfo>
        <StatusBadge tone={routePlan.weatherAvailable ? 'blue' : 'slate'}>{routePlan.weatherAvailable ? 'Live Weather' : 'Weather Default'}</StatusBadge>
        {deliveryOrderIds.length > 0 && <StatusBadge tone="blue">{deliveryOrderIds.length} selected deliveries</StatusBadge>}
      </div>
      {(actionError || validation?.blockingReasons.length) ? <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{actionError || validation?.blockingReasons.join('; ')}</div> : validation?.warnings.length ? <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm font-semibold text-amber-800">{validation.warnings.join('; ')}</div> : null}
      <div className="grid min-w-0 gap-5 xl:grid-cols-[430px_1fr]">
        <div className="min-w-0 space-y-5">
          <Card title="Configuration">
            <label className="block text-sm font-bold text-fleet-muted">Origin Depot<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold"><option>Colombo Depot</option></select></label>
            <label className="mt-4 block text-sm font-bold text-fleet-muted">Assigned Vehicle<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold" onChange={(event) => setSelectedVehicleId(event.target.value)} value={effectiveVehicleId}><option value="">Select a vehicle</option>{data.vehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.registrationNumber} · {vehicle.category} · {vehicle.risk} risk</option>)}</select></label>
            <label className="mt-4 block text-sm font-bold text-fleet-muted">Assigned Driver<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold" onChange={(event) => setSelectedDriverId(event.target.value)} value={selectedDriverId}><option value="">Select an enrolled driver</option>{data.drivers.map((driver) => <option key={driver.id} value={driver.id}>@{driver.username} · {driver.full_name}</option>)}</select></label>
            <p className="mt-4 rounded-lg bg-slate-50 p-3 text-xs font-medium leading-5 text-fleet-muted">Choose an enrolled driver and an eligible vehicle. Optimization links the selected parcels; dispatch assigns that route and its deliveries to both.</p>
          </Card>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Stat label="Total Cost" value={routePlan.distance} />
            <Stat label="Estimated ETA" value={routePlan.eta} />
            <Stat label="Capacity Use" value={`${routePlan.capacityUse}%`} progress={routePlan.capacityUse} />
            <Stat label="Total Stops" value={`${routePlan.stops.length}`} />
          </div>
        </div>
        <div className="min-w-0">
        <Card action={<SecondaryButton disabled={!effectiveVehicleId || !selectedDriverId} onClick={recalculate}><RefreshCcw className="h-4 w-4" /> Recalculate</SecondaryButton>} title="Optimized Route Path">
          <GoogleMapPanel
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
