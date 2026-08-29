import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Ban, Box, CheckCircle2, Download, MapPinned, Play, RefreshCcw, ShieldCheck, Truck } from 'lucide-react'
import { CargoBay3D } from '../components/CargoBay3D'
import { OpenStreetMapPanel } from '../components/OpenStreetMapPanel'
import { Card, DataTable, ErrorState, LoadingState, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { generationAction } from '../features/loadOptimization/planningState'
import { buildCandidateRoutePreview } from '../features/loadOptimization/candidateRoutePreview'
import type { ConsolidationPlanningState, LoadEligibility, LoadJob, LoadPlan, ParcelConsolidation, ParetoOption, VirtualLoad } from '../features/loadOptimization/types'
import { authService } from '../services/authService'
import { loadOptimizationService } from '../services/loadOptimizationService'
import { canAccess } from '../utils/permissions'

function saveDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

const candidateNames = ['Efficient Fleet', 'Balanced Capacity', 'Maximum Buffer']

export function LoadOptimizationPage({ embedded = false, onContinueToRoute }: { embedded?: boolean; onContinueToRoute?: (planId: string) => void } = {}) {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const user = authService.getSession()
  const [consolidations, setConsolidations] = useState<ParcelConsolidation[]>([])
  const [selectedConsolidationId, setSelectedConsolidationId] = useState(searchParams.get('consolidation') ?? '')
  const [planningState, setPlanningState] = useState<ConsolidationPlanningState | null>(null)
  const [eligibility, setEligibility] = useState<LoadEligibility | null>(null)
  const [activePlan, setActivePlan] = useState<LoadPlan | null>(null)
  const [job, setJob] = useState<LoadJob | null>(null)
  const [selectedOptionId, setSelectedOptionId] = useState('')
  const [activeLoad, setActiveLoad] = useState<VirtualLoad | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actionBusy, setActionBusy] = useState(false)

  const applyPlan = (plan: LoadPlan | null) => {
    setActivePlan(plan)
    const optionId = plan?.selected_option?.option_id ?? plan?.pareto_options[0]?.option_id ?? ''
    setSelectedOptionId(optionId)
    const option = plan?.selected_option ?? plan?.pareto_options.find((item) => item.option_id === optionId)
    setActiveLoad(option?.loads[0] ?? null)
  }

  const loadWorkspace = async (requestedId = selectedConsolidationId, silent = false) => {
    if (!silent) setLoading(true)
    setError('')
    try {
      const result = await loadOptimizationService.listConsolidations()
      const visible = result.items.filter((item) => !['superseded', 'cancelled'].includes(item.status))
      setConsolidations(visible)
      const selectedId = requestedId && visible.some((item) => item.consolidation_id === requestedId) ? requestedId : visible[0]?.consolidation_id ?? ''
      if (!selectedId) {
        setSelectedConsolidationId('')
        setPlanningState(null)
        setEligibility(null)
        applyPlan(null)
        setJob(null)
        return
      }
      const state = await loadOptimizationService.planningState(selectedId)
      setSelectedConsolidationId(selectedId)
      setPlanningState(state)
      setJob(state.job)
      applyPlan(state.plan)
      setEligibility({
        batch_key: `colombo_central_branch:${state.consolidation.delivery_date}:${state.consolidation.delivery_period}`,
        delivery_date: state.consolidation.delivery_date,
        delivery_period: state.consolidation.delivery_period,
        eligible_count: state.consolidation.parcel_count,
        exception_count: state.plan?.exceptions.length ?? 0,
        excluded_count: 0,
        eligible_orders: [], exceptions: [], excluded_orders: [],
      })
      const updated = new URLSearchParams(searchParams)
      updated.set('consolidation', selectedId)
      setSearchParams(updated, { replace: true })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to load the planning workspace')
    } finally {
      if (!silent) setLoading(false)
    }
  }

  useEffect(() => {
    queueMicrotask(() => { void loadWorkspace() })
    // Initial state is rehydrated from the server by consolidation ID.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!job || !['queued', 'running'].includes(job.status) || !selectedConsolidationId) return
    const timer = window.setInterval(async () => {
      try {
        const next = await loadOptimizationService.getJob(job.job_id)
        setJob(next)
        if (!['queued', 'running'].includes(next.status)) await loadWorkspace(selectedConsolidationId, true)
      } catch (reason) {
        setError(reason instanceof Error ? reason.message : 'Unable to refresh optimization progress')
      }
    }, 2000)
    return () => window.clearInterval(timer)
    // Polling follows the persisted job returned by planning-state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job?.job_id, job?.status, selectedConsolidationId])

  const generate = async () => {
    if (!planningState?.can_generate || !selectedConsolidationId) return
    setActionBusy(true)
    setError('')
    try {
      const result = await loadOptimizationService.createJob({
        delivery_date: planningState.consolidation.delivery_date,
        delivery_period: planningState.consolidation.delivery_period,
        consolidation_id: selectedConsolidationId,
        seed: 17,
      })
      setJob(result.job)
      if (result.plan) applyPlan(result.plan)
      await loadWorkspace(selectedConsolidationId, true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to generate candidates')
    } finally {
      setActionBusy(false)
    }
  }

  const approve = async (optionId: string) => {
    if (!activePlan || activePlan.status !== 'review_required') return
    setActionBusy(true)
    setError('')
    try {
      const updated = await loadOptimizationService.approve(activePlan.plan_id, optionId)
      applyPlan(updated)
      await loadWorkspace(selectedConsolidationId, true)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Unable to approve this candidate')
    } finally {
      setActionBusy(false)
    }
  }

  const continueToRoute = () => {
    if (!activePlan || activePlan.status !== 'approved') return
    if (onContinueToRoute) onContinueToRoute(activePlan.plan_id)
    else navigate(`/route-planning?workspace=dispatch&plan=${encodeURIComponent(activePlan.plan_id)}`)
  }

  const selectedOption = activePlan?.status === 'approved'
    ? activePlan.selected_option
    : activePlan?.pareto_options.find((item) => item.option_id === selectedOptionId) ?? activePlan?.pareto_options[0]
  const candidatePreview = useMemo(
    () => buildCandidateRoutePreview(selectedOption, planningState?.consolidation.parcel_points ?? []),
    [planningState?.consolidation.parcel_points, selectedOption],
  )
  const routeMarkers = useMemo(() => [{
    id: 'colombo-branch', label: 'B', title: 'FleetOpt Colombo Branch', subtitle: 'Fixed origin and return point',
    position: { latitude: 6.9271, longitude: 79.8612 }, color: '#047857', kind: 'branch' as const,
  }, ...candidatePreview.dropMarkers], [candidatePreview.dropMarkers])

  if (loading) return <LoadingState label="Loading load planning workspace" />
  if (error && !planningState) return <ErrorState message={error} onRetry={loadWorkspace} />

  const canGenerate = canAccess(user, 'load_optimization.generate')
  const canApprove = canAccess(user, 'load_optimization.approve')
  const canCancel = canAccess(user, 'load_optimization.cancel')
  const canExport = canAccess(user, 'reports.export')
  const generation = generationAction(planningState?.status ?? 'not_started')
  const selectedConsolidation = planningState?.consolidation

  return <div>
    {!embedded && <PageHeader
      action={<div className="flex flex-wrap gap-2"><SecondaryButton onClick={() => void loadWorkspace()}><RefreshCcw className="h-4 w-4" /> Refresh status</SecondaryButton>{activePlan && canExport && <SecondaryButton onClick={async () => { const file = await loadOptimizationService.export(activePlan.plan_id); saveDownload(file.blob, file.filename) }}><Download className="h-4 w-4" /> Export plan</SecondaryButton>}{canGenerate && <PrimaryButton disabled={actionBusy || !generation.enabled || !selectedConsolidationId} onClick={generate}><Play className="h-4 w-4" /> {generation.label}</PrimaryButton>}</div>}
      description="Review one fixed candidate set for each consolidated delivery batch, approve a safe load arrangement, then continue to route dispatch."
      eyebrow={<StatusBadge tone={activePlan?.status === 'approved' ? 'green' : job?.status === 'failed' ? 'red' : 'blue'}>{planningState?.status?.replaceAll('_', ' ') ?? 'Batch selection'}</StatusBadge>}
      title="Parcel Load Planning"
    />}
    {embedded && <div className="mb-5 flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-xl font-black text-fleet-ink">Consolidation planning candidates</h2><p className="mt-1 text-sm font-semibold text-fleet-muted">Each consolidation creates one controlled candidate set. Approve one arrangement before route planning.</p></div><div className="flex flex-wrap gap-2"><SecondaryButton onClick={() => void loadWorkspace()}><RefreshCcw className="h-4 w-4" /> Refresh</SecondaryButton>{canGenerate && <PrimaryButton disabled={actionBusy || !generation.enabled || !selectedConsolidationId} onClick={generate}><Play className="h-4 w-4" /> {generation.label}</PrimaryButton>}</div></div>}

    {error && <div className="mb-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>}
    <section className="mb-5 grid gap-4 rounded-lg border border-fleet-line bg-white p-5 shadow-card md:grid-cols-[minmax(0,1.35fr)_minmax(180px,0.65fr)_minmax(210px,0.7fr)] md:items-end">
      <label className="text-sm font-bold text-fleet-muted">Consolidation ID<select className="mt-2 min-h-11 w-full rounded-lg border border-fleet-line px-3 text-fleet-ink" onChange={(event) => void loadWorkspace(event.target.value)} value={selectedConsolidationId}><option value="">Select a consolidation ID</option>{consolidations.map((item) => <option key={item.consolidation_id} value={item.consolidation_id}>{item.consolidation_id} - {item.parcel_count} parcels</option>)}</select></label>
      <ReadOnlyField label="Delivery date" value={selectedConsolidation?.delivery_date ?? '-'} />
      <ReadOnlyField label="Delivery period" value={selectedConsolidation?.delivery_period === 'second_half' ? 'Second Half - 13:00-17:00' : 'First Half - 08:00-12:00'} />
    </section>

    <div className="mb-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Summary icon={Box} label="Consolidated parcels" tone="blue" value={String(eligibility?.eligible_count ?? 0)} /><Summary icon={ShieldCheck} label="Exceptions" tone={(activePlan?.exceptions.length ?? 0) ? 'amber' : 'green'} value={String(activePlan?.exceptions.length ?? 0)} /><Summary icon={Truck} label="Candidate loads" tone="blue" value={String(selectedOption?.loads.length ?? 0)} /><Summary icon={CheckCircle2} label="Decision" tone={activePlan?.status === 'approved' ? 'green' : 'amber'} value={activePlan?.status === 'approved' ? 'Approved' : activePlan ? 'Review' : 'Pending'} /></div>

    {job && ['queued', 'running'].includes(job.status) && <section className="mb-5 rounded-lg border border-blue-200 bg-blue-50 p-4"><div className="flex items-center justify-between text-sm font-bold text-blue-900"><span>{job.stage.replaceAll('_', ' ')}</span><span>{job.progress_percent}%</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-blue-100"><div className="h-full rounded-full bg-blue-600 transition-all duration-500" style={{ width: `${job.progress_percent}%` }} /></div><p className="mt-2 text-xs font-semibold text-blue-800">This job continues on the server if you leave or refresh this page.</p>{canCancel && <button className="mt-3 inline-flex items-center gap-2 text-sm font-bold text-red-700" onClick={async () => { setJob(await loadOptimizationService.cancelJob(job.job_id)); await loadWorkspace(selectedConsolidationId, true) }} type="button"><Ban className="h-4 w-4" /> Cancel job</button>}</section>}

    {activePlan && <section className="mb-5"><div className="mb-3 flex flex-wrap items-end justify-between gap-3"><div><h2 className="text-[15px] font-black text-fleet-ink">Candidate decision</h2><p className="text-sm text-fleet-muted">Compare all three arrangements. Approval locks the selected load plan and disables the alternatives.</p></div>{activePlan.status === 'approved' && <PrimaryButton onClick={continueToRoute}><MapPinned className="h-4 w-4" /> Route &amp; Dispatch</PrimaryButton>}</div><div className="grid gap-4 lg:grid-cols-3">{activePlan.pareto_options.slice(0, 3).map((option, index) => <CandidateCard approved={activePlan.status === 'approved' && activePlan.selected_option?.option_id === option.option_id} canApprove={canApprove} disabled={actionBusy || activePlan.status === 'approved'} key={option.option_id} name={candidateNames[index] ?? option.label} onApprove={() => void approve(option.option_id)} onSelect={() => { setSelectedOptionId(option.option_id); setActiveLoad(option.loads[0] ?? null) }} option={option} selected={selectedOptionId === option.option_id} />)}</div></section>}

    <div className="grid min-w-0 gap-5 xl:grid-cols-2"><Card title={`Candidate route preview - ${candidatePreview.dropMarkers.length} delivery stops`}><OpenStreetMapPanel className="min-h-[390px]" markers={routeMarkers} polylines={candidatePreview.polylines} /><p className="mt-3 text-xs font-semibold text-fleet-muted">Numbered markers show only parcels included in this candidate. Exception parcels are excluded. Final road geometry is created after compatible physical vehicles are confirmed.</p></Card><section className="overflow-hidden rounded-lg border border-fleet-line bg-white shadow-card"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-fleet-line px-5 py-3.5"><h2 className="text-[15px] font-bold">Cargo placement and loading order</h2>{activeLoad && <StatusBadge tone="blue">{activeLoad.parcel_count} parcels</StatusBadge>}</div><CargoBay3D load={activeLoad} />{activeLoad && <div className="border-t border-fleet-line p-4 text-xs font-semibold text-fleet-muted">Loading sequence: {activeLoad.loading_sequence.join(' -> ')}</div>}</section></div>

    {selectedOption && <Card className="mt-5" title="Virtual loads in selected candidate"><DataTable headers={['Load', 'Type', 'Parcels', 'Weight', 'Volume', 'Handling']}>{selectedOption.loads.map((load) => <tr className={activeLoad?.load_id === load.load_id ? 'bg-blue-50/60' : ''} key={load.load_id}><td className="px-5 py-4"><button className="font-black text-fleet-blue" onClick={() => setActiveLoad(load)} type="button">{load.load_id}</button></td><td className="px-5 py-4 font-semibold">{load.vehicle_type_code.replaceAll('_', ' ')}</td><td className="px-5 py-4">{load.parcel_count}</td><td className="px-5 py-4">{load.used_weight_kg.toFixed(1)} / {load.capacity_kg} kg</td><td className="px-5 py-4">{load.used_volume_m3.toFixed(2)} / {load.capacity_m3} m3</td><td className="px-5 py-4">{load.hazardous ? 'Hazmat' : load.requires_refrigeration ? 'Refrigerated' : 'Standard'}</td></tr>)}</DataTable></Card>}
  </div>
}

function CandidateCard({ option, name, selected, approved, disabled, canApprove, onSelect, onApprove }: { option: ParetoOption; name: string; selected: boolean; approved: boolean; disabled: boolean; canApprove: boolean; onSelect: () => void; onApprove: () => void }) {
  return <article className={`rounded-lg border bg-white p-4 shadow-card ${approved ? 'border-emerald-400 ring-2 ring-emerald-100' : selected ? 'border-blue-400 ring-2 ring-blue-100' : 'border-fleet-line'}`}><button className="w-full text-left" onClick={onSelect} type="button"><div className="flex items-center justify-between gap-2"><h3 className="text-sm font-black">{name}</h3>{approved ? <StatusBadge tone="green">Approved</StatusBadge> : selected ? <StatusBadge tone="blue">Selected</StatusBadge> : null}</div><div className="mt-4 grid grid-cols-2 gap-3 text-sm"><Metric label="Vehicles" value={option.objectives.vehicle_count} /><Metric label="Route preview" value={`${(option.objectives.estimated_route_km ?? 0).toFixed(1)} km`} /><Metric label="Spare capacity" value={`${option.objectives.unused_volume_m3.toFixed(2)} m3`} /><Metric label="Exceptions" value={option.objectives.unassigned_parcels} /></div></button>{canApprove && !approved && <div className="mt-4 [&>button]:w-full [&>button]:justify-center"><PrimaryButton disabled={disabled} onClick={onApprove}><CheckCircle2 className="h-4 w-4" /> Approve this candidate</PrimaryButton></div>}</article>
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return <div className="rounded-md bg-slate-50 p-2"><div className="text-[11px] font-bold uppercase text-fleet-muted">{label}</div><div className="mt-1 font-black text-fleet-ink">{value}</div></div>
}

function ReadOnlyField({ label, value }: { label: string; value: string }) {
  return <div><div className="text-sm font-bold text-fleet-muted">{label}</div><div className="mt-2 flex min-h-11 items-center rounded-lg border border-fleet-line bg-slate-50 px-3 font-bold">{value}</div></div>
}

function Summary({ icon: Icon, label, value, tone }: { icon: typeof Box; label: string; value: string; tone: 'blue' | 'green' | 'amber' }) {
  const classes = tone === 'green' ? 'bg-emerald-50 text-emerald-700' : tone === 'amber' ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'
  return <div className="flex items-center justify-between rounded-lg border border-fleet-line bg-white p-5 shadow-card"><div><div className="text-xs font-bold uppercase text-fleet-muted">{label}</div><div className="mt-2 text-2xl font-black">{value}</div></div><span className={`grid h-11 w-11 place-items-center rounded-lg ${classes}`}><Icon className="h-5 w-5" /></span></div>
}
