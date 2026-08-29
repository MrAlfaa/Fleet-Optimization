import { ArrowRight, ClipboardClock, ClipboardList, History, Search, ShieldAlert, TriangleAlert, Wrench } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DataTable, EmptyState, ErrorState, LoadingState, PageHeader, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'
import { VehicleIdentity } from '../components/VehicleIdentity'
import { summarizeMaintenanceByVehicle } from '../features/maintenance/maintenanceSummary'
import { useAsyncData } from '../hooks/useAsyncData'
import { fleetService } from '../services/fleetService'

export function MaintenancePage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [state, setState] = useState('all')
  const { data, error, loading, reload } = useAsyncData(async () => {
    const [records, vehicles, reviews, inspectionPage] = await Promise.all([
      fleetService.listMaintenanceRecords(), fleetService.listVehicles(), fleetService.listPredictionReviews(), fleetService.listInspections(),
    ])
    return { records, vehicles, reviews, inspections: inspectionPage.items }
  }, [])
  const allSummaries = useMemo(() => summarizeMaintenanceByVehicle(data?.vehicles ?? [], data?.records ?? []), [data])
  const summaries = useMemo(() => allSummaries.filter((summary) => {
    const matchesQuery = `${summary.vehicle.registrationNumber} ${summary.vehicle.vehicleCode} ${summary.vehicle.model}`.toLowerCase().includes(query.toLowerCase())
    return matchesQuery && (state === 'all' || (state === 'overdue' && summary.overdue > 0) || (state === 'open' && summary.open > 0) || (state === 'clear' && summary.open === 0))
  }), [allSummaries, query, state])
  if (loading) return <LoadingState label="Preparing maintenance command center..." />
  if (error || !data) return <ErrorState message={error ?? 'Unable to load maintenance operations'} onRetry={reload} />

  const activeInspections = data.inspections.filter((item) => item.isActive)
  const holdVehicleIds = new Set([...activeInspections.map((item) => item.vehicleId), ...data.vehicles.filter((vehicle) => vehicle.status === 'Maintenance').map((vehicle) => vehicle.id), ...data.reviews.filter((review) => review.status === 'pending' || review.status === 'confirmed').map((review) => review.vehicleId)])
  const awaitingAssignment = activeInspections.filter((item) => item.status === 'pending').length
  const inspectionsInProgress = activeInspections.filter((item) => item.status === 'in_progress').length
  const activeWorkOrders = data.records.filter((record) => record.workOrderStatus === 'planned' || record.workOrderStatus === 'approved' || record.workOrderStatus === 'in_progress').length
  const overdueVehicles = allSummaries.filter((item) => item.overdue > 0).length
  const vehicleFor = (vehicleId: string) => data.vehicles.find((item) => item.id === vehicleId)

  return <div className="min-w-0 space-y-5">
    <PageHeader action={<><button className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-bold text-slate-700 shadow-sm hover:bg-slate-50" onClick={() => navigate('/maintenance/history')} type="button"><History className="h-4 w-4" />Maintenance History</button><button className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-bold text-blue-700 shadow-sm hover:bg-blue-50" onClick={() => navigate('/maintenance/work-orders')} type="button"><Wrench className="h-4 w-4" />Work Orders</button><PrimaryButton onClick={() => navigate('/maintenance/inspections')}><ClipboardList className="h-4 w-4" />Inspection Queue</PrimaryButton></>} description="Monitor service holds, assign inspections, and review fleet service state from one operational workspace." title="Maintenance Command Center" />
    {overdueVehicles > 0 && <div className="flex items-center gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-800"><TriangleAlert className="h-5 w-5 shrink-0" /><strong>{overdueVehicles} vehicle{overdueVehicles === 1 ? '' : 's'} have overdue service work that requires attention before dispatch.</strong></div>}
    <section aria-label="Maintenance operation summary" className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={ShieldAlert} label="Service holds" tone="red" value={holdVehicleIds.size} /><Metric icon={ClipboardClock} label="Awaiting assignment" tone="amber" value={awaitingAssignment} /><Metric icon={ClipboardList} label="Inspections in progress" tone="blue" value={inspectionsInProgress} /><Metric icon={Wrench} label="Active work orders" tone="slate" value={activeWorkOrders} /></section>
    <section className="min-w-0 rounded-lg border border-slate-200 bg-white shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-5"><div><h2 className="font-extrabold text-slate-950">Inspection queue</h2><p className="mt-1 text-sm text-slate-500">Vehicles currently held for structured maintenance review.</p></div><button className="inline-flex min-h-10 items-center gap-2 rounded-lg border border-slate-200 px-3 text-sm font-bold text-blue-700 transition hover:bg-blue-50" onClick={() => navigate('/maintenance/inspections')} title="Open complete inspection queue" type="button">View all <ArrowRight className="h-4 w-4" /></button></div>
      {activeInspections.length ? <DataTable headers={['Vehicle', 'Priority', 'Inspection areas', 'Status', 'Created']}>{activeInspections.slice(0, 5).map((inspection) => { const vehicle = vehicleFor(inspection.vehicleId); return <tr className="cursor-pointer transition hover:bg-blue-50/50" key={inspection.id} onClick={() => navigate('/maintenance/inspections')}><td className="px-5 py-4"><div className="font-extrabold">{vehicle?.registrationNumber ?? 'Unknown vehicle'}</div><div className="text-xs text-slate-500">{vehicle?.vehicleCode ?? inspection.vehicleId}</div></td><td className="px-5 py-4"><StatusBadge tone={inspection.priority === 'critical' ? 'red' : inspection.priority === 'high' ? 'amber' : 'blue'}>{inspection.priority}</StatusBadge></td><td className="max-w-80 px-5 py-4 text-sm font-semibold">{inspection.inspectionAreas.join(', ') || 'General vehicle condition'}</td><td className="px-5 py-4"><StatusBadge tone={inspection.status === 'in_progress' ? 'blue' : 'amber'}>{inspection.status.replaceAll('_', ' ')}</StatusBadge></td><td className="whitespace-nowrap px-5 py-4 text-sm font-semibold">{formatDate(inspection.createdAt)}</td></tr> })}</DataTable> : <div className="p-5"><EmptyState description="Vehicles added from their Risk Assessment workspace will appear here." title="No active inspections" /></div>}
    </section>
    <section className="min-w-0 space-y-4">
      <div><h2 className="text-lg font-extrabold text-slate-950">Vehicle service state</h2><p className="mt-1 text-sm text-slate-500">Open service work and recent maintenance activity by vehicle.</p></div>
      <div className="flex min-w-0 flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-card"><label className="flex min-w-[220px] flex-1 items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2"><Search className="h-4 w-4 text-slate-400" /><input aria-label="Search maintenance vehicles" className="min-w-0 flex-1 bg-transparent text-sm outline-none" onChange={(event) => setQuery(event.target.value)} placeholder="Registration, fleet code, or vehicle" value={query} /></label><select aria-label="Maintenance state" className="min-h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" onChange={(event) => setState(event.target.value)} value={state}><option value="all">All vehicles</option><option value="overdue">Overdue</option><option value="open">Open work</option><option value="clear">No open work</option></select></div>
      {summaries.length === 0 ? <EmptyState description="Adjust the search or service-state filter." title="No matching vehicles" /> : <DataTable headers={['Vehicle', 'Risk', 'Open work', 'Overdue', 'Last activity', 'State']}>{summaries.map((summary) => <tr className="cursor-pointer transition hover:bg-blue-50/50" key={summary.vehicle.id} onClick={() => navigate(`/vehicles/${summary.vehicle.id}?tab=maintenance`)} tabIndex={0} onKeyDown={(event) => { if (event.key === 'Enter') navigate(`/vehicles/${summary.vehicle.id}?tab=maintenance`) }}><td className="px-5 py-4"><VehicleIdentity size="sm" vehicle={summary.vehicle} /></td><td className="px-5 py-4"><RiskBadge risk={summary.vehicle.risk} /></td><td className="px-5 py-4 text-lg font-extrabold">{summary.open}</td><td className="px-5 py-4 text-lg font-extrabold text-red-600">{summary.overdue}</td><td className="px-5 py-4"><div className="font-bold">{summary.latestRecord?.service ?? 'No service record'}</div><div className="text-xs text-slate-500">{summary.latestRecord?.date ?? 'No recent activity'}</div></td><td className="px-5 py-4"><StatusBadge tone={summary.overdue ? 'red' : summary.open ? 'amber' : 'green'}>{summary.overdue ? 'Action required' : summary.open ? 'Scheduled' : 'Clear'}</StatusBadge></td></tr>)}</DataTable>}
    </section>
  </div>
}

function Metric({ icon: Icon, label, value, tone }: { icon: typeof Wrench; label: string; value: number; tone: 'red' | 'amber' | 'blue' | 'slate' }) { const styles = { red: 'bg-red-50 text-red-700', amber: 'bg-amber-50 text-amber-700', blue: 'bg-blue-50 text-blue-700', slate: 'bg-slate-100 text-slate-700' }; return <div className="min-w-0 rounded-lg border border-slate-200 bg-white p-5 shadow-card"><div className="flex items-center justify-between gap-3"><span className="text-sm font-bold text-slate-600">{label}</span><span className={`grid h-9 w-9 place-items-center rounded-lg ${styles[tone]}`}><Icon className="h-5 w-5" /></span></div><div className="mt-4 text-3xl font-extrabold text-slate-950">{value}</div></div> }
function formatDate(value: string) { const date = new Date(value); return Number.isNaN(date.getTime()) ? 'Unknown' : date.toLocaleString() }
