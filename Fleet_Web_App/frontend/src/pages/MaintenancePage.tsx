import { Search, TriangleAlert } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, RiskBadge, StatusBadge } from '../components/UI'
import { VehicleIdentity } from '../components/VehicleIdentity'
import { summarizeMaintenanceByVehicle } from '../features/maintenance/maintenanceSummary'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'

export function MaintenancePage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [state, setState] = useState('all')
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [records, vehicles] = await Promise.all([fleetService.listMaintenanceRecords(), fleetService.listVehicles()])
    return { records, vehicles }
  }, [])
  const summaries = useMemo(() => summarizeMaintenanceByVehicle(data?.vehicles ?? [], data?.records ?? []).filter((summary) => {
    const matchesQuery = `${summary.vehicle.registrationNumber} ${summary.vehicle.vehicleCode} ${summary.vehicle.model}`.toLowerCase().includes(query.toLowerCase())
    const matchesState = state === 'all' || (state === 'overdue' && summary.overdue > 0) || (state === 'open' && summary.open > 0) || (state === 'clear' && summary.open === 0)
    return matchesQuery && matchesState
  }), [data, query, state])
  const overdueVehicles = summaries.filter((item) => item.overdue > 0).length

  if (loading) return <LoadingState label="Preparing fleet maintenance workspace..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load maintenance data'} onRetry={reload} />

  return <div>
    <PageHeader description="Review maintenance readiness by vehicle, then open a vehicle workspace for service details." title="Fleet Maintenance" />
    {overdueVehicles > 0 && <div className="mb-5 flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700"><TriangleAlert className="h-5 w-5 shrink-0" /><strong>{overdueVehicles} vehicle{overdueVehicles === 1 ? '' : 's'} require overdue service attention before dispatch.</strong></div>}
    <div className="mb-4 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-card">
      <label className="flex min-w-[260px] flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"><Search className="h-4 w-4 text-slate-400" /><input aria-label="Search maintenance vehicles" className="w-full bg-transparent text-sm outline-none" onChange={(event) => setQuery(event.target.value)} placeholder="Search registration, fleet code, or model" value={query} /></label>
      <select aria-label="Maintenance state" className="min-h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" onChange={(event) => setState(event.target.value)} value={state}><option value="all">All vehicles</option><option value="overdue">Overdue</option><option value="open">Open work</option><option value="clear">No open work</option></select>
    </div>
    {summaries.length === 0 ? <EmptyState title="No matching vehicles" description="Adjust the search or maintenance-state filter." /> : <DataTable headers={['Vehicle', 'Health', 'Open Work', 'Overdue', 'Last Activity', 'Outstanding Cost', 'State']}>
      {summaries.map((summary) => <tr className="cursor-pointer hover:bg-blue-50/50" key={summary.vehicle.id} onClick={() => navigate(`/maintenance/vehicle/${summary.vehicle.id}`)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') navigate(`/maintenance/vehicle/${summary.vehicle.id}`) }}>
        <td className="px-5 py-4"><VehicleIdentity size="sm" vehicle={summary.vehicle} /></td><td className="px-5 py-4"><RiskBadge risk={summary.vehicle.risk} /></td><td className="px-5 py-4 text-lg font-extrabold">{summary.open}</td><td className="px-5 py-4 text-lg font-extrabold text-red-600">{summary.overdue}</td>
        <td className="px-5 py-4"><div className="font-bold">{summary.latestRecord?.service ?? 'No service record'}</div><div className="text-xs text-slate-500">{summary.latestRecord?.date ?? 'Maintenance history is clear'}</div></td><td className="px-5 py-4 font-bold">${summary.outstandingCost.toFixed(2)}</td><td className="px-5 py-4"><StatusBadge tone={summary.overdue ? 'red' : summary.open ? 'amber' : 'green'}>{summary.overdue ? 'Action required' : summary.open ? 'Scheduled' : 'Clear'}</StatusBadge></td>
      </tr>)}
    </DataTable>}
  </div>
}
