import { Layers, Search } from 'lucide-react'
import { Card, MapPanel, PageHeader, StatusBadge } from '../components/UI'
import { demandZones } from '../data/mockData'

export function ZonesPage() {
  return (
    <div>
      <PageHeader
        description="Visualize predicted demand, active delivery density, overload scores, and neighboring zone influence."
        title="Zone Demand Heatmap"
      />
      <div className="grid gap-5 xl:grid-cols-[300px_1fr]">
        <aside className="space-y-4">
          <Card title="Global Demand">
            <div className="text-sm font-bold uppercase text-fleet-muted">Total Predicted</div>
            <div className="mt-1 text-4xl font-black">12,450</div>
            <div className="mt-4 text-sm font-bold uppercase text-fleet-muted">Critical Zones</div>
            <div className="text-3xl font-black text-fleet-red">4 <span className="text-sm">+2</span></div>
          </Card>
          <Card title="Active Zones">
            <div className="space-y-3">
              {demandZones.slice(0, 4).map((zone) => (
                <div className={`rounded-2xl border p-4 ${zone.risk === 'critical' ? 'border-red-200 bg-red-50' : zone.risk === 'high' ? 'border-amber-200 bg-amber-50' : 'border-emerald-200 bg-emerald-50'}`} key={zone.id}>
                  <div className="flex items-center justify-between"><div className="font-black">{zone.name}</div><StatusBadge tone={zone.risk === 'critical' ? 'red' : zone.risk === 'high' ? 'amber' : 'green'}>{zone.risk}</StatusBadge></div>
                  <div className="mt-3 text-sm font-semibold">Predicted: {zone.predicted.toLocaleString()}</div>
                  <div className="text-sm font-semibold">Actual: {zone.actual.toLocaleString()}</div>
                  <div className="mt-3 h-2 rounded-full bg-white"><div className="h-full rounded-full bg-current" style={{ width: `${Math.min(zone.overloadScore, 100)}%` }} /></div>
                </div>
              ))}
            </div>
          </Card>
        </aside>
        <div className="rounded-2xl border border-fleet-line bg-white p-4 shadow-card">
          <div className="mb-4 flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2 rounded-xl border border-fleet-line bg-slate-50 px-3 py-2 text-sm font-bold text-fleet-muted"><Search className="h-4 w-4" /> Search Zones...</div>
            <StatusBadge tone="red">Critical</StatusBadge>
            <StatusBadge tone="amber">Warning</StatusBadge>
            <StatusBadge tone="green">Stable</StatusBadge>
            <Layers className="ml-auto h-5 w-5 text-fleet-muted" />
          </div>
          <MapPanel className="min-h-[720px]">
            <div className="absolute left-[35%] top-[37%] h-52 w-80 rotate-[-8deg] border-4 border-red-500 bg-red-500/24" />
            <div className="absolute left-[57%] top-[27%] h-72 w-64 rotate-[35deg] border-4 border-amber-500 bg-amber-400/25" />
            <div className="absolute left-[20%] top-[47%] h-64 w-72 rotate-[-12deg] border-4 border-emerald-500 bg-emerald-400/22" />
            <div className="glass-panel absolute bottom-5 right-5 rounded-2xl p-4">
              <div className="mb-2 font-black">Neighboring Influence</div>
              <div className="grid grid-cols-2 gap-2 text-xs font-bold">
                <div className="rounded-xl bg-red-50 p-3 text-red-700">From North +15% Load</div>
                <div className="rounded-xl bg-emerald-50 p-3 text-emerald-700">To West -5% Spill</div>
              </div>
            </div>
          </MapPanel>
        </div>
      </div>
    </div>
  )
}
