import { Archive, ArchiveRestore, ChevronRight, Pencil, Plus, Power, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'
import { formatNumber } from '../utils/format'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'
import { VEHICLE_CATEGORIES } from '../data/sriLankaZones'
import { VehicleForm } from '../components/VehicleForm'
import { VehicleIdentity } from '../components/VehicleIdentity'
import type { Vehicle } from '../types'
import { authService } from '../services/authService'
import { canAccess } from '../utils/permissions'

export function VehiclesPage() {
  const currentUser = authService.getSession()
  const canCreate = canAccess(currentUser, 'vehicles.create')
  const [risk, setRisk] = useState('all')
  const [category, setCategory] = useState('all')
  const [status, setStatus] = useState('all')
  const [showCreate, setShowCreate] = useState(false)
  const [editing, setEditing] = useState<Vehicle | null>(null)
  const [actionError, setActionError] = useState('')
  const [busyId, setBusyId] = useState('')
  const { data: vehicles, error, loading, reload } = useAsyncData(() => fleetService.listVehicles(), [])
  const filtered = useMemo(() => {
    const items = vehicles ?? []
    return items.filter((vehicle) =>
      (risk === 'all' || vehicle.risk === risk)
      && (category === 'all' || vehicle.type === category)
      && (status === 'all' || vehicle.status === status),
    )
  }, [category, risk, status, vehicles])

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={reload} />

  return (
    <div>
      <PageHeader
        action={canCreate ? <PrimaryButton onClick={() => setShowCreate(true)}><Plus className="h-4 w-4" /> Add Vehicle</PrimaryButton> : undefined}
        description="Manage and monitor your fleet inventory in real-time."
        title="Vehicle Registry"
      />
      <div className="mb-4 rounded-2xl border border-fleet-line bg-white p-4 shadow-card">
        <div className="flex flex-wrap items-center gap-3">
          <SlidersHorizontal className="h-5 w-5 text-fleet-muted" />
          <select className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setRisk(event.target.value)} value={risk}>
            <option value="all">All Risks</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <select className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setCategory(event.target.value)} value={category}>
            <option value="all">All Categories</option>
            {VEHICLE_CATEGORIES.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
          </select>
          <select className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" onChange={(event) => setStatus(event.target.value)} value={status}>
            <option value="all">All Statuses</option>
            <option value="Active">Active</option>
            <option value="Maintenance">Maintenance</option>
            <option value="Offline">Offline</option>
            <option value="Retired">Retired</option>
          </select>
          <span className="w-full text-sm font-bold text-fleet-muted sm:ml-auto sm:w-auto">{filtered.length} vehicles visible</span>
        </div>
      </div>

      {actionError && <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm font-semibold text-red-700">{actionError}</div>}

      {filtered.length === 0 ? (
        <EmptyState title="No vehicles found" description="Create a vehicle or adjust the risk filter." />
      ) : (
        <div className="hidden md:block"><DataTable headers={['Vehicle', 'Model', 'Assigned Driver', 'Mileage', 'Status', 'Risk', 'Actions']}>
          {filtered.map((vehicle) => (
            <tr className="transition duration-200 hover:bg-blue-50/70 hover:shadow-[inset_3px_0_0_#2563eb]" key={vehicle.id}>
              <td className="px-5 py-3"><Link to={`/vehicles/${vehicle.id}`}><VehicleIdentity size="sm" vehicle={vehicle} /></Link></td>
              <td className="px-5 py-4 font-semibold">{vehicle.model}</td>
              <td className="px-5 py-4 font-semibold">{vehicle.assignedDriver}</td>
              <td className="px-5 py-4">{formatNumber(vehicle.mileage)} km</td>
              <td className="px-5 py-4">
                <StatusBadge tone={vehicle.status === 'Active' ? 'green' : vehicle.status === 'Maintenance' ? 'amber' : 'blue'}>{vehicle.status}</StatusBadge>
              </td>
              <td className="px-5 py-4"><RiskBadge risk={vehicle.risk} /></td>
              <td className="px-5 py-4"><VehicleActions busy={busyId === vehicle.id} onActivate={async () => { setBusyId(vehicle.id); setActionError(''); try { await fleetService.updateVehicle(vehicle.id, { status: 'active' }); await reload() } catch (action) { setActionError(action instanceof Error ? action.message : 'Unable to activate vehicle') } finally { setBusyId('') } }} onEdit={() => setEditing(vehicle)} onLifecycle={async () => { setBusyId(vehicle.id); setActionError(''); try { if (vehicle.status === 'Retired') await fleetService.restoreVehicle(vehicle.id); else await fleetService.retireVehicle(vehicle.id, 'Retired from Vehicle Registry'); await reload() } catch (action) { setActionError(action instanceof Error ? action.message : 'Unable to update vehicle lifecycle') } finally { setBusyId('') } }} vehicle={vehicle} /></td>
            </tr>
          ))}
        </DataTable></div>
      )}

      {filtered.length > 0 && <div className="grid gap-3 md:hidden">{filtered.map((vehicle) => <article className="min-w-0 rounded-lg border border-fleet-line bg-white p-4 shadow-card" key={vehicle.id}><div className="flex min-w-0 items-start justify-between gap-3"><Link className="min-w-0" to={`/vehicles/${vehicle.id}`}><VehicleIdentity size="sm" vehicle={vehicle} /></Link><RiskBadge risk={vehicle.risk} /></div><dl className="mt-4 grid grid-cols-2 gap-3 text-sm"><div><dt className="text-xs font-semibold text-fleet-muted">Mileage</dt><dd className="mt-1 font-bold">{formatNumber(vehicle.mileage)} km</dd></div><div><dt className="text-xs font-semibold text-fleet-muted">Status</dt><dd className="mt-1"><StatusBadge tone={vehicle.status === 'Active' ? 'green' : vehicle.status === 'Maintenance' ? 'amber' : 'slate'}>{vehicle.status}</StatusBadge></dd></div></dl><div className="mt-4 border-t border-fleet-line pt-3"><VehicleActions busy={busyId === vehicle.id} onActivate={async () => { setBusyId(vehicle.id); try { await fleetService.updateVehicle(vehicle.id, { status: 'active' }); await reload() } catch (action) { setActionError(action instanceof Error ? action.message : 'Unable to activate vehicle') } finally { setBusyId('') } }} onEdit={() => setEditing(vehicle)} onLifecycle={async () => { setBusyId(vehicle.id); try { if (vehicle.status === 'Retired') await fleetService.restoreVehicle(vehicle.id); else await fleetService.retireVehicle(vehicle.id); await reload() } catch (action) { setActionError(action instanceof Error ? action.message : 'Unable to update vehicle') } finally { setBusyId('') } }} vehicle={vehicle} /></div></article>)}</div>}

      {showCreate && <VehicleForm onCancel={() => setShowCreate(false)} onCreated={async () => { setShowCreate(false); await reload() }} />}
      {editing && <VehicleForm onCancel={() => setEditing(null)} onSaved={async () => { setEditing(null); await reload() }} vehicle={editing} />}
    </div>
  )
}

function VehicleActions({ vehicle, busy, onEdit, onLifecycle, onActivate }: { vehicle: Vehicle; busy: boolean; onEdit: () => void; onLifecycle: () => void; onActivate: () => void }) {
  const canUpdate = canAccess(authService.getSession(), 'vehicles.update')
  const actionClass = 'grid h-9 w-9 place-items-center rounded-lg text-slate-500 transition duration-200 hover:-translate-y-0.5 hover:shadow-sm focus-visible:ring-2 focus-visible:ring-blue-300'
  return <div className="flex items-center gap-1"><Link aria-label={`View ${vehicle.registrationNumber}`} className={`${actionClass} hover:bg-blue-50 hover:text-blue-700`} title="View vehicle details" to={`/vehicles/${vehicle.id}`}><ChevronRight className="h-4 w-4" /></Link>{canUpdate && <><button aria-label={`Edit ${vehicle.registrationNumber}`} className={`${actionClass} hover:bg-blue-50 hover:text-blue-700`} onClick={onEdit} title="Edit vehicle" type="button"><Pencil className="h-4 w-4" /></button>{vehicle.status === 'Offline' && <button aria-label={`Activate ${vehicle.registrationNumber}`} className={`${actionClass} text-emerald-600 hover:bg-emerald-50 disabled:opacity-50`} disabled={busy} onClick={onActivate} title="Activate inspected vehicle" type="button"><Power className="h-4 w-4" /></button>}<button aria-label={`${vehicle.status === 'Retired' ? 'Restore' : 'Retire'} ${vehicle.registrationNumber}`} className={`${actionClass} hover:bg-amber-50 hover:text-amber-700 disabled:opacity-50`} disabled={busy} onClick={onLifecycle} title={vehicle.status === 'Retired' ? 'Restore vehicle' : 'Retire vehicle'} type="button">{vehicle.status === 'Retired' ? <ArchiveRestore className="h-4 w-4" /> : <Archive className="h-4 w-4" />}</button></>}</div>
}
