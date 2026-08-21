import { Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'
import { VehicleIdentity } from '../components/VehicleIdentity'
import { VehicleSubsystemList } from '../components/VehicleSubsystemList'
import { VehicleComponentDialog } from '../components/VehicleComponentDialog'
import { MaintenanceRecordDialog } from '../components/MaintenanceRecordDialog'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import type { VehiclePart } from '../types'


export function VehicleDetailPage() {
  const { vehicleId = '' } = useParams()
  const [selectedPart, setSelectedPart] = useState<VehiclePart | null>(null)
  const [showComponent, setShowComponent] = useState(false)
  const [maintenancePart, setMaintenancePart] = useState<VehiclePart | null>(null)
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [vehicle, parts, maintenanceRecords] = await Promise.all([
      fleetService.getVehicle(vehicleId),
      fleetService.listVehicleParts(vehicleId, true),
      fleetService.listMaintenanceRecords({ vehicle_id: vehicleId }),
    ])
    return { vehicle, parts, maintenanceRecords }
  }, [vehicleId])

  if (loading) return <LoadingState />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load vehicle detail'} onRetry={reload} />

  const { vehicle, parts, maintenanceRecords } = data
  const activeParts = parts.filter((item) => item.isActive !== false)
  const openRecords = maintenanceRecords.filter((record) => record.status !== 'Completed')
  const nextService = activeParts.map((part) => part.predictedNext).find((value) => value !== 'No prediction') ?? 'Not scheduled'

  return <div className="space-y-5">
    <section className="flex flex-col gap-5 rounded-lg border border-slate-200 bg-white p-5 shadow-card lg:flex-row lg:items-center lg:justify-between">
      <VehicleIdentity size="lg" vehicle={vehicle} />
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge tone={vehicle.status === 'Active' ? 'green' : vehicle.status === 'Maintenance' ? 'amber' : 'blue'}>{vehicle.status}</StatusBadge>
        <RiskBadge risk={vehicle.risk} />
        <Link className="rounded-lg border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700 hover:bg-slate-50" to={`/maintenance/vehicle/${vehicle.id}`}>Maintenance workspace</Link>
        <PrimaryButton onClick={() => setShowComponent(true)}><Plus className="h-4 w-4" />Add part</PrimaryButton>
      </div>
    </section>

    <section className="grid overflow-hidden rounded-lg border border-slate-200 bg-white sm:grid-cols-2 xl:grid-cols-4">
      <Summary label="Overall health" value={vehicle.risk === 'low' ? 'Healthy' : vehicle.risk === 'critical' ? 'Critical' : 'Monitor'} />
      <Summary label="Predictive risk" value={vehicle.risk} />
      <Summary label="Open maintenance" value={String(openRecords.length)} />
      <Summary label="Next service" value={nextService} />
    </section>

    <div className="space-y-5">
      <section className="min-w-0">
        <div className="mb-3 flex items-end justify-between gap-4"><div><h1 className="text-xl font-extrabold text-slate-950">EV part health</h1><p className="mt-1 text-sm text-slate-500">Review part condition, service history, and predicted attention windows.</p></div><span className="shrink-0 text-sm font-bold text-slate-500">{activeParts.length} monitored</span></div>
        {activeParts.length ? <VehicleSubsystemList onSelectPart={setSelectedPart} parts={activeParts} /> : <EmptyState description="Add or restore an EV part to monitor its condition." title="No active parts" />}
      </section>

      <aside className="min-w-0 rounded-lg border border-slate-200 bg-white">
        <div className="border-b border-slate-200 px-5 py-4"><h2 className="font-extrabold text-slate-950">Maintenance timeline</h2></div>
        <div className="space-y-5 p-5">
          {maintenanceRecords.length === 0 && <div className="text-sm font-semibold text-slate-500">No maintenance records for this vehicle.</div>}
          {maintenanceRecords.slice(0, 8).map((record) => <div className="relative border-l-2 border-slate-200 pl-4" key={record.id}><span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full bg-blue-600 ring-4 ring-white" /><div className="text-xs font-bold text-slate-500">{record.date}</div><div className="mt-1 font-extrabold text-slate-950">{record.service}</div><div className="text-sm font-medium text-slate-500">{record.technician}</div></div>)}
        </div>
      </aside>
    </div>

    {(showComponent || selectedPart) && <VehicleComponentDialog onClose={() => { setShowComponent(false); setSelectedPart(null) }} onCreateMaintenance={(part) => { setSelectedPart(null); setMaintenancePart(part) }} onSaved={reload} part={selectedPart} parts={parts} vehicleId={vehicle.id} />}
    {maintenancePart && <MaintenanceRecordDialog onClose={() => setMaintenancePart(null)} onSaved={reload} part={maintenancePart} vehicle={vehicle} />}
  </div>
}


function Summary({ label, value }: { label: string; value: string }) {
  return <div className="border-b border-slate-200 p-5 last:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0"><div className="text-xs font-bold uppercase text-slate-500">{label}</div><div className="mt-2 truncate text-xl font-extrabold capitalize text-slate-950">{value}</div></div>
}
