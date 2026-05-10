import { Filter, Plus, TriangleAlert } from 'lucide-react'
import { useState } from 'react'
import { maintenanceRecords } from '../data/mockData'
import { DataTable, PageHeader, PrimaryButton, StatusBadge } from '../components/UI'

export function MaintenancePage() {
  const [tab, setTab] = useState('All Records')
  const records = maintenanceRecords.filter((record) => tab === 'All Records' || record.status === tab)
  return (
    <div>
      <PageHeader
        action={<PrimaryButton><Plus className="h-4 w-4" /> Add Maintenance Record</PrimaryButton>}
        description="Review completed services, overdue work, and upcoming predictive maintenance schedules."
        title="Maintenance History"
      />
      <div className="mb-5 flex items-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
        <TriangleAlert className="h-5 w-5" />
        <div className="font-extrabold">2 critical services overdue</div>
        <div className="text-sm font-semibold">TRK-2041 brake replacement and VAN-3810 transmission fluid exceeded service bounds.</div>
      </div>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {['All Records', 'Completed', 'Pending Parts', 'Overdue'].map((item) => (
          <button
            className={`rounded-xl px-4 py-2 text-sm font-extrabold transition ${tab === item ? 'bg-fleet-blue text-white shadow-soft' : 'bg-white text-fleet-muted ring-1 ring-fleet-line hover:bg-slate-50'}`}
            key={item}
            onClick={() => setTab(item)}
            type="button"
          >
            {item}
          </button>
        ))}
        <button className="ml-auto inline-flex items-center gap-2 rounded-xl border border-fleet-line bg-white px-4 py-2 text-sm font-bold text-fleet-muted" type="button">
          <Filter className="h-4 w-4" /> Filter
        </button>
      </div>
      <DataTable headers={['Service Date', 'Vehicle', 'Part / Service', 'Technician', 'Cost', 'Status']}>
        {records.map((record) => (
          <tr className="hover:bg-blue-50/40" key={record.id}>
            <td className="px-5 py-4 font-bold">{record.date}</td>
            <td className="px-5 py-4 font-black text-fleet-blue">{record.vehicle}</td>
            <td className="px-5 py-4 font-semibold">{record.service}</td>
            <td className="px-5 py-4">{record.technician}</td>
            <td className="px-5 py-4 font-bold">{record.cost}</td>
            <td className="px-5 py-4">
              <StatusBadge tone={record.status === 'Completed' ? 'green' : record.status === 'Overdue' ? 'red' : 'amber'}>
                {record.status}
              </StatusBadge>
            </td>
          </tr>
        ))}
      </DataTable>
    </div>
  )
}
