import { Box, Download, Eye, PackageCheck } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { CargoBay3D } from '../components/CargoBay3D'
import { Card, DataTable, ErrorState, LoadingState, PageHeader, SecondaryButton, StatusBadge } from '../components/UI'
import type { LoadPlan, VirtualLoad } from '../features/loadOptimization/types'
import { loadOptimizationService } from '../services/loadOptimizationService'

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

export function LoadPlansPage() {
  const { planId } = useParams()
  const [searchParams] = useSearchParams()
  const requestedLoadId = searchParams.get('load')
  const navigate = useNavigate()
  const [plans, setPlans] = useState<LoadPlan[]>([])
  const [selectedPlan, setSelectedPlan] = useState<LoadPlan | null>(null)
  const [selectedLoad, setSelectedLoad] = useState<VirtualLoad | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadPlans = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await loadOptimizationService.listPlans()
      setPlans(response.items)
      const plan = planId ? await loadOptimizationService.getPlan(planId) : response.items[0] ?? null
      setSelectedPlan(plan)
      const availableLoads = plan?.selected_option?.loads ?? plan?.pareto_options[0]?.loads ?? []
      setSelectedLoad(availableLoads.find((load) => load.load_id === requestedLoadId) ?? availableLoads[0] ?? null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load saved plans')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    queueMicrotask(() => { void loadPlans() })
    // The selected route parameter owns the saved-plan query.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId, requestedLoadId])

  const loads = useMemo(() => selectedPlan?.selected_option?.loads ?? selectedPlan?.pareto_options[0]?.loads ?? [], [selectedPlan])
  if (loading) return <LoadingState label="Loading saved load plans" />
  if (error && !plans.length) return <ErrorState message={error} onRetry={loadPlans} />

  return <div className="space-y-5">
    <PageHeader
      title="Load Plans"
      description="Inspect approved and pending vehicle-by-vehicle loading instructions."
      action={selectedPlan ? <SecondaryButton onClick={async () => { const file = await loadOptimizationService.export(selectedPlan.plan_id); saveDownload(file.blob, file.filename) }}><Download className="h-4 w-4" /> Export plan</SecondaryButton> : undefined}
    />
    {error && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>}
    <Card title="Plan selection">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <label className="text-sm font-semibold">Saved plan
          <select className="mt-2 w-full rounded-lg border border-fleet-line px-3 py-2.5" onChange={(event) => navigate(`/load-plans/${event.target.value}`)} value={selectedPlan?.plan_id ?? ''}>
            <option value="">Select a plan</option>
            {plans.map((plan) => <option key={plan.plan_id} value={plan.plan_id}>{plan.plan_id} · {plan.delivery_date} · {plan.delivery_period.replace('_', ' ')} · revision {plan.revision}</option>)}
          </select>
        </label>
        <SecondaryButton onClick={() => navigate('/load-optimization')}><PackageCheck className="h-4 w-4" /> Open optimization</SecondaryButton>
      </div>
    </Card>

    {selectedPlan ? <>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <PlanMetric label="Plan" value={`Revision ${selectedPlan.revision}`} />
        <PlanMetric label="Status" value={selectedPlan.status.replaceAll('_', ' ')} />
        <PlanMetric label="Parcels" value={String(loads.reduce((sum, load) => sum + load.parcel_count, 0))} />
        <PlanMetric label="Vehicles" value={String(loads.length)} />
        <PlanMetric label="Assigned" value={`${loads.filter((load) => load.assigned_vehicle_id).length}/${loads.length}`} />
      </div>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
        <Card title="Vehicle selection">
          <div className="mb-4 flex flex-wrap gap-2">{loads.map((load) => <button className={`rounded-lg border px-3 py-2 text-sm font-bold ${selectedLoad?.load_id === load.load_id ? 'border-blue-300 bg-blue-50 text-blue-700' : 'border-fleet-line'}`} key={load.load_id} onClick={() => setSelectedLoad(load)} type="button"><Box className="mr-2 inline h-4 w-4" />{load.vehicle_type_code} · {load.parcel_count}</button>)}</div>
          <DataTable headers={['Load order', 'Parcel', 'Dimensions', 'Position', 'Handling']}>
            {(selectedLoad?.loading_sequence ?? []).map((parcelId, index) => {
              const placement = selectedLoad?.placements.find((item) => item.parcel_id === parcelId)
              return <tr key={parcelId}><td className="px-5 py-3 font-bold">{index + 1}</td><td className="px-5 py-3 font-semibold">{parcelId}</td><td className="px-5 py-3">{placement ? `${placement.length_cm} × ${placement.width_cm} × ${placement.height_cm} cm` : 'Not available'}</td><td className="px-5 py-3">{placement ? `${placement.x_cm}, ${placement.y_cm}, ${placement.z_cm}` : 'Not available'}</td><td className="px-5 py-3">{placement?.fragile ? <StatusBadge tone="amber">Fragile</StatusBadge> : <StatusBadge tone="slate">Standard</StatusBadge>}</td></tr>
            })}
          </DataTable>
        </Card>
        <Card title="3D cargo bay"><CargoBay3D load={selectedLoad} /></Card>
      </div>
    </> : <Card><div className="grid min-h-[240px] place-items-center text-center"><div><Eye className="mx-auto h-8 w-8 text-slate-400" /><p className="mt-3 text-sm text-fleet-muted">No saved load plan is available.</p></div></div></Card>}
  </div>
}

function PlanMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-lg border border-fleet-line bg-white p-4 shadow-card"><div className="text-xs font-bold uppercase text-fleet-muted">{label}</div><div className="mt-2 truncate text-lg font-black capitalize">{value}</div></div>
}
