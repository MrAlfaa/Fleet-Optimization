import { Play, RefreshCcw, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { Card, DataTable, MapPanel, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { routePlan } from '../data/mockData'

export function RoutePlanningPage() {
  const [override, setOverride] = useState('')
  const [vehicle, setVehicle] = useState(routePlan.vehicle)
  return (
    <div>
      <PageHeader
        action={<PrimaryButton><Play className="h-4 w-4" /> Dispatch Route</PrimaryButton>}
        description="Configure and optimize routes before finalizing dispatch orders."
        title="Dispatch Configuration"
      />
      <div className="mb-5 flex items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
        <TriangleAlert className="mt-0.5 h-5 w-5" />
        <div><div className="font-black">High-Risk Vehicle Selected</div><div className="text-sm font-semibold">{routePlan.warning}</div></div>
      </div>
      <div className="grid gap-5 xl:grid-cols-[430px_1fr]">
        <div className="space-y-5">
          <Card title="Configuration">
            <label className="block text-sm font-bold text-fleet-muted">Origin Depot<select className="mt-2 min-h-11 w-full rounded-xl border border-fleet-line px-3 font-semibold"><option>North Hub (Facility A)</option></select></label>
            <label className="mt-4 block text-sm font-bold text-fleet-muted">Assigned Vehicle<select className="mt-2 min-h-11 w-full rounded-xl border border-red-200 bg-red-50 px-3 font-semibold text-red-700" onChange={(event) => setVehicle(event.target.value)} value={vehicle}><option>VAN-3810</option><option>CAB-1024</option><option>TRK-2041</option></select></label>
            <label className="mt-4 block text-sm font-bold text-fleet-muted">Override Reason<textarea className="mt-2 min-h-24 w-full rounded-xl border border-fleet-line px-3 py-2 font-semibold outline-none focus:ring-4 focus:ring-blue-100" onChange={(event) => setOverride(event.target.value)} placeholder="Required if dispatching a high-risk vehicle..." value={override} /></label>
          </Card>
          <div className="grid grid-cols-2 gap-4">
            <Stat label="Total Distance" value={routePlan.distance} />
            <Stat label="Estimated ETA" value={routePlan.eta} />
            <Stat label="Capacity Use" value={`${routePlan.capacityUse}%`} progress={routePlan.capacityUse} />
            <Stat label="Total Stops" value={`${routePlan.stops.length}`} />
          </div>
        </div>
        <Card action={<SecondaryButton><RefreshCcw className="h-4 w-4" /> Recalculate</SecondaryButton>} title="Optimized Route Path">
          <MapPanel className="mb-4 min-h-[260px]">
            <div className="absolute left-[25%] top-[54%] h-3 w-[48%] -rotate-6 rounded-full bg-fleet-blue shadow-[0_0_22px_rgba(29,78,216,0.45)]" />
          </MapPanel>
          <DataTable headers={['Seq', 'Location / Entity', 'Est. Arrival', 'Load Drop', 'Status']}>
            {routePlan.stops.map((stop) => (
              <tr key={stop.sequence}>
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
  )
}

function Stat({ label, value, progress }: { label: string; value: string; progress?: number }) {
  return <div className="rounded-2xl border border-fleet-line bg-white p-5 shadow-card"><div className="text-sm font-bold text-fleet-muted">{label}</div><div className="mt-2 text-2xl font-black">{value}</div>{progress && <div className="mt-3 h-2 rounded-full bg-slate-100"><div className="h-full rounded-full bg-fleet-blue" style={{ width: `${progress}%` }} /></div>}</div>
}
