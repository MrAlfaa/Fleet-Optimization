import { Plus, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useMemo, useState } from 'react'
import { vehicles } from '../data/mockData'
import { DataTable, PageHeader, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'
import { formatNumber, statusDotClass } from '../utils/format'

export function VehiclesPage() {
  const [risk, setRisk] = useState('all')
  const filtered = useMemo(() => (risk === 'all' ? vehicles : vehicles.filter((vehicle) => vehicle.risk === risk)), [risk])

  return (
    <div>
      <PageHeader
        action={<PrimaryButton><Plus className="h-4 w-4" /> Add Vehicle</PrimaryButton>}
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
          <select className="rounded-xl border border-fleet-line px-3 py-2 text-sm font-bold">
            <option>All Statuses</option>
            <option>Active</option>
            <option>Maintenance</option>
            <option>In Transit</option>
          </select>
          <span className="ml-auto text-sm font-bold text-fleet-muted">{filtered.length} vehicles visible</span>
        </div>
      </div>

      <DataTable headers={['Vehicle Number', 'Model', 'Type', 'Assigned Driver', 'Mileage', 'Status', 'Risk', 'Actions']}>
        {filtered.map((vehicle) => (
          <tr className="transition hover:bg-blue-50/40" key={vehicle.id}>
            <td className="px-5 py-4 font-black text-fleet-blue">
              <Link to={`/vehicles/${vehicle.id}`}>{vehicle.number}</Link>
            </td>
            <td className="px-5 py-4 font-semibold">{vehicle.model}</td>
            <td className="px-5 py-4 text-fleet-muted">{vehicle.type}</td>
            <td className="px-5 py-4 font-semibold">{vehicle.assignedDriver}</td>
            <td className="px-5 py-4">{formatNumber(vehicle.mileage)} km</td>
            <td className="px-5 py-4">
              <StatusBadge tone={vehicle.status === 'Active' ? 'green' : vehicle.status === 'Maintenance' ? 'amber' : 'blue'}>{vehicle.status}</StatusBadge>
            </td>
            <td className="px-5 py-4">
              <span className="flex items-center gap-2"><span className={statusDotClass(vehicle.risk)} /> {vehicle.risk}</span>
            </td>
            <td className="px-5 py-4"><RiskBadge risk={vehicle.risk} /></td>
          </tr>
        ))}
      </DataTable>
    </div>
  )
}
