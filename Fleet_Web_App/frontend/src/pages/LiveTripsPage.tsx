import { Filter, Plus, RadioTower } from 'lucide-react'
import { Card, MapPanel, PageHeader, PrimaryButton, SecondaryButton, StatusBadge } from '../components/UI'
import { tripEvents } from '../data/mockData'

export function LiveTripsPage() {
  return (
    <div>
      <PageHeader
        action={<div className="flex gap-3"><SecondaryButton><Filter className="h-4 w-4" /> Filter</SecondaryButton><PrimaryButton><Plus className="h-4 w-4" /> New Dispatch</PrimaryButton></div>}
        description="Monitoring 14 active trips across 3 regions."
        title="Active Deployments"
      />
      <div className="grid gap-5 xl:grid-cols-[1fr_430px]">
        <Card action={<div className="flex gap-2"><StatusBadge tone="green">12 On Time</StatusBadge><StatusBadge tone="amber">2 Delayed</StatusBadge></div>} title="Live Fleet Map">
          <MapPanel className="min-h-[760px]">
            <div className="absolute left-[24%] top-[66%] h-5 w-5 rounded-full bg-red-500 ring-4 ring-white" />
            <div className="absolute left-[44%] top-[38%] h-5 w-5 rounded-full bg-fleet-blue ring-4 ring-white" />
            <div className="absolute bottom-5 right-5 grid gap-2">
              <button className="grid h-9 w-9 place-items-center rounded-lg bg-white font-black shadow" type="button">+</button>
              <button className="grid h-9 w-9 place-items-center rounded-lg bg-white font-black shadow" type="button">-</button>
            </div>
          </MapPanel>
        </Card>
        <aside className="space-y-5">
          <Card title="TRK-492">
            <div className="mb-3 flex items-center gap-2"><StatusBadge tone="green">En Route</StatusBadge><span className="text-sm font-bold text-fleet-muted">Driver: Marcus Johnson</span></div>
            <div className="grid grid-cols-2 gap-3">
              <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs font-black uppercase text-fleet-muted">ETA</div><div className="text-2xl font-black">14:30</div></div>
              <div className="rounded-2xl bg-slate-50 p-4"><div className="text-xs font-black uppercase text-fleet-muted">Next Stop</div><div className="font-black">Dist. Center Alpha</div></div>
            </div>
            <div className="mt-4 h-2 rounded-full bg-slate-100"><div className="h-full w-[65%] rounded-full bg-fleet-blue" /></div>
            <div className="mt-2 text-right text-xs font-black text-fleet-muted">65% Complete</div>
          </Card>
          <Card action={<button className="text-xs font-black text-fleet-blue" type="button">View All</button>} title="Trip Log">
            <div className="space-y-5">
              {tripEvents.map((event) => (
                <div className="flex gap-3" key={event.id}>
                  <RadioTower className={`mt-1 h-4 w-4 ${event.severity === 'warning' ? 'text-fleet-red' : 'text-fleet-blue'}`} />
                  <div className="flex-1">
                    <div className="flex items-center justify-between"><div className={`font-black ${event.severity === 'warning' ? 'text-fleet-red' : ''}`}>{event.title}</div><div className="text-xs font-bold text-fleet-muted">{event.time}</div></div>
                    <p className="text-sm font-medium text-fleet-muted">{event.description}</p>
                    {event.severity === 'warning' && <button className="mt-2 text-sm font-black text-fleet-blue" type="button">Apply Reroute</button>}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </aside>
      </div>
    </div>
  )
}
