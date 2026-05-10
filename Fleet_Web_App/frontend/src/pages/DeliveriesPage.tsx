import { Plus, SlidersHorizontal } from 'lucide-react'
import { useMemo, useState } from 'react'
import { deliveries } from '../data/mockData'
import { DataTable, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'

export function DeliveriesPage() {
  const [selected, setSelected] = useState<string[]>([])
  const selectedCount = selected.length
  const selectedSet = useMemo(() => new Set(selected), [selected])
  const toggle = (id: string) => setSelected((items) => (items.includes(id) ? items.filter((item) => item !== id) : [...items, id]))

  return (
    <div>
      <PageHeader
        action={<PrimaryButton><Plus className="h-4 w-4" /> Add Delivery Point</PrimaryButton>}
        description="Manage and route incoming delivery orders across active zones."
        title="Delivery Management"
      />
      <div className="mb-4 flex flex-wrap items-center gap-3 rounded-2xl border border-fleet-line bg-white p-4 shadow-card">
        <button className="inline-flex items-center gap-2 rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" type="button"><SlidersHorizontal className="h-4 w-4" /> All Zones</button>
        <button className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold" type="button">Sort by Priority</button>
        <div className="ml-auto text-sm font-black text-fleet-blue">Route Selected ({selectedCount})</div>
        <button className="rounded-xl bg-blue-100 px-4 py-2 text-sm font-black text-fleet-blue" type="button">Assign Batch</button>
      </div>
      <DataTable headers={['', 'Customer / Ref', 'Priority', 'Time Window', 'Zone', 'Location', 'Status']}>
        {deliveries.map((order) => (
          <tr className={selectedSet.has(order.id) ? 'bg-blue-50' : 'hover:bg-blue-50/40'} key={order.id}>
            <td className="px-5 py-4"><input checked={selectedSet.has(order.id)} onChange={() => toggle(order.id)} type="checkbox" /></td>
            <td className="px-5 py-4"><div className="font-black">{order.customer}</div><div className="text-xs font-bold text-fleet-muted">{order.id.toUpperCase()}</div></td>
            <td className="px-5 py-4"><StatusBadge tone={order.priority === 'Critical' ? 'red' : order.priority === 'High' ? 'amber' : 'slate'}>{order.priority}</StatusBadge></td>
            <td className="px-5 py-4 font-semibold">{order.timeWindow}</td>
            <td className="px-5 py-4"><StatusBadge tone="slate">{order.zone}</StatusBadge></td>
            <td className="px-5 py-4 text-fleet-muted">{order.location}</td>
            <td className="px-5 py-4"><StatusBadge tone={order.status === 'Routed' ? 'green' : order.status === 'In Transit' ? 'blue' : 'slate'}>{order.status}</StatusBadge></td>
          </tr>
        ))}
      </DataTable>
    </div>
  )
}
