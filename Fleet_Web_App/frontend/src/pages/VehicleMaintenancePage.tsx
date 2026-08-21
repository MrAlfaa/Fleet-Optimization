import { ArrowLeft, Ban, CheckCircle2, Pencil, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, RiskBadge, SecondaryButton, StatusBadge } from '../components/UI'
import { VehicleIdentity } from '../components/VehicleIdentity'
import { VehicleSubsystemList } from '../components/VehicleSubsystemList'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import type { MaintenanceRecord, VehiclePart } from '../types'
import { VehicleComponentDialog } from '../components/VehicleComponentDialog'
import { MaintenanceRecordDialog } from '../components/MaintenanceRecordDialog'

export function VehicleMaintenancePage() {
  const { vehicleId = '' } = useParams()
  const [busyId, setBusyId] = useState('')
  const [selectedPart, setSelectedPart] = useState<VehiclePart | null>(null)
  const [showAddPart, setShowAddPart] = useState(false)
  const [maintenancePart, setMaintenancePart] = useState<VehiclePart | null>(null)
  const [editingRecord, setEditingRecord] = useState<MaintenanceRecord | null>(null)
  const [showMaintenance, setShowMaintenance] = useState(false)
  const { data, error, loading, reload } = useAsyncData(async () => { const [vehicle, parts, records] = await Promise.all([fleetService.getVehicle(vehicleId), fleetService.listVehicleParts(vehicleId, true), fleetService.listMaintenanceRecords({ vehicle_id: vehicleId })]); return { vehicle, parts, records } }, [vehicleId])
  if (loading) return <LoadingState label="Loading vehicle maintenance workspace..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load vehicle maintenance'} onRetry={reload} />
  const open = data.records.filter((record) => !['Completed', 'Cancelled'].includes(record.status))
  const activeParts = data.parts.filter((part) => part.isActive !== false)
  const complete = async (id: string) => { setBusyId(id); try { await fleetService.completeMaintenance(id); await reload() } finally { setBusyId('') } }
  return <div className="space-y-5">
    <PageHeader action={<Link className="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold" to="/maintenance"><ArrowLeft className="h-4 w-4" />Fleet maintenance</Link>} description="Part condition, open work, and complete service history for one vehicle." title="Vehicle Maintenance Workspace" />
    <section className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-white p-5 shadow-card lg:flex-row lg:items-center lg:justify-between"><VehicleIdentity size="lg" vehicle={data.vehicle} /><div className="flex items-center gap-2"><RiskBadge risk={data.vehicle.risk} /><StatusBadge tone={open.some((r) => r.status === 'Overdue') ? 'red' : open.length ? 'amber' : 'green'}>{open.length} open</StatusBadge></div></section>
    <section className="min-w-0"><div className="mb-3 flex flex-wrap items-center justify-between gap-3"><h2 className="text-lg font-extrabold">EV part condition</h2><SecondaryButton onClick={() => setShowAddPart(true)}><Plus className="h-4 w-4" />Add part</SecondaryButton></div>{activeParts.length ? <VehicleSubsystemList onSelectPart={setSelectedPart} parts={activeParts} /> : <EmptyState title="No active parts" description="Add or restore an EV part to monitor its condition." />}</section>
    <section className="min-w-0 rounded-lg border border-slate-200 bg-white shadow-card"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5"><div><h2 className="font-extrabold">Service records</h2><p className="text-sm text-slate-500">Open and completed work remains attached to {data.vehicle.registrationNumber}.</p></div><SecondaryButton onClick={() => setShowMaintenance(true)}><Plus className="h-4 w-4" />Create record</SecondaryButton></div>{data.records.length ? <DataTable headers={['Date', 'Part / Service', 'Priority', 'Technician', 'Cost', 'Status', 'Actions']}>{data.records.map((record) => { const closed = ['Completed','Cancelled'].includes(record.status); return <tr key={record.id}><td className="px-5 py-4 font-bold">{record.date}</td><td className="px-5 py-4"><div className="font-extrabold">{record.partName}</div><div className="text-xs text-slate-500">{record.maintenanceType}</div></td><td className="px-5 py-4 capitalize">{record.priority}</td><td className="px-5 py-4">{record.technician}</td><td className="px-5 py-4 font-bold">{record.cost}</td><td className="px-5 py-4"><StatusBadge tone={record.status === 'Completed' ? 'green' : record.status === 'Cancelled' ? 'slate' : record.status === 'Overdue' ? 'red' : 'amber'}>{record.status}</StatusBadge></td><td className="px-5 py-4"><div className="flex gap-1"><button aria-label="Edit maintenance" className="rounded-lg p-2 transition hover:-translate-y-0.5 hover:bg-blue-50" disabled={closed} onClick={() => setEditingRecord(record)} title="Edit maintenance record" type="button"><Pencil className="h-4 w-4" /></button><button aria-label="Complete maintenance" className="rounded-lg p-2 text-emerald-700 transition hover:-translate-y-0.5 hover:bg-emerald-50" disabled={closed || busyId === record.id} onClick={() => complete(record.id)} title="Complete maintenance record" type="button"><CheckCircle2 className="h-4 w-4" /></button><button aria-label="Cancel maintenance" className="rounded-lg p-2 text-red-700 transition hover:-translate-y-0.5 hover:bg-red-50" disabled={closed || busyId === record.id} onClick={async () => { setBusyId(record.id); try { await fleetService.cancelMaintenance(record.id); await reload() } finally { setBusyId('') } }} title="Cancel maintenance record" type="button"><Ban className="h-4 w-4" /></button></div></td></tr>})}</DataTable> : <div className="p-5"><EmptyState title="No maintenance history" description="Create a maintenance record from this vehicle workspace." /></div>}</section>
    {(showAddPart || selectedPart) && <VehicleComponentDialog onClose={() => { setShowAddPart(false); setSelectedPart(null) }} onCreateMaintenance={(part) => { setSelectedPart(null); setMaintenancePart(part) }} onSaved={reload} part={selectedPart} parts={data.parts} vehicleId={vehicleId} />}
    {(showMaintenance || maintenancePart || editingRecord) && <MaintenanceRecordDialog onClose={() => { setShowMaintenance(false); setMaintenancePart(null); setEditingRecord(null) }} onSaved={reload} part={maintenancePart} record={editingRecord} vehicle={data.vehicle} />}
  </div>
}
