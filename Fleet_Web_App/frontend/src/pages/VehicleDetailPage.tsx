import { CheckCircle2, Wrench } from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { maintenanceRecords, vehicleParts, vehicles } from '../data/mockData'
import { Card, PageHeader, PrimaryButton, RiskBadge, StatusBadge } from '../components/UI'

export function VehicleDetailPage() {
  const { vehicleId = 'cab-1024' } = useParams()
  const [showModal, setShowModal] = useState(false)
  const vehicle = vehicles.find((item) => item.id === vehicleId) ?? vehicles[0]

  return (
    <div>
      <PageHeader
        action={<PrimaryButton onClick={() => setShowModal(true)}><CheckCircle2 className="h-4 w-4" /> Mark as Maintained</PrimaryButton>}
        description={`${vehicle.model} • ${vehicle.type} • ${vehicle.mileage.toLocaleString()} km`}
        eyebrow={<RiskBadge risk={vehicle.risk} />}
        title={vehicle.number}
      />
      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">
          {vehicleParts.map((part) => (
            <button
              className="rounded-2xl border border-fleet-line bg-white p-5 text-left shadow-card transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-soft"
              key={part.id}
              type="button"
            >
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2 text-lg font-black"><Wrench className="h-5 w-5 text-fleet-muted" /> {part.name}</div>
                <RiskBadge risk={part.risk} />
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div><div className="font-bold text-fleet-muted">Last Service</div><div className="font-extrabold">{part.lastService}</div></div>
                <div><div className="font-bold text-fleet-muted">Failures</div><div className="font-extrabold">{part.failures}</div></div>
              </div>
              <div className="mt-4 rounded-xl bg-slate-50 p-3">
                <div className="text-xs font-black uppercase text-fleet-muted">Predicted next</div>
                <div className="mt-1 font-black text-fleet-blue">{part.predictedNext}</div>
              </div>
              <p className="mt-3 text-sm font-medium text-fleet-muted">{part.note}</p>
            </button>
          ))}
        </div>
        <Card title="Maintenance Log">
          <div className="space-y-4">
            {maintenanceRecords.slice(0, 4).map((record) => (
              <div className="relative border-l-2 border-slate-200 pl-4" key={record.id}>
                <span className="absolute -left-[7px] top-1 h-3 w-3 rounded-full bg-fleet-blue ring-4 ring-white" />
                <div className="text-xs font-bold text-fleet-muted">{record.date}</div>
                <div className="mt-1 font-black">{record.service}</div>
                <div className="text-sm font-medium text-fleet-muted">{record.vehicle} • {record.technician}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-slate-950/45 p-4">
          <div className="w-full max-w-lg rounded-3xl bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-start justify-between">
              <div>
                <h3 className="text-2xl font-black">Complete maintenance</h3>
                <p className="mt-1 text-sm font-semibold text-fleet-muted">This updates the local frontend state demo workflow.</p>
              </div>
              <StatusBadge tone="blue">Placeholder baseline</StatusBadge>
            </div>
            <textarea className="min-h-28 w-full rounded-2xl border border-fleet-line p-3 text-sm font-semibold outline-none focus:ring-4 focus:ring-blue-100" placeholder="Service notes..." />
            <div className="mt-5 flex justify-end gap-3">
              <button className="rounded-xl px-4 py-2 text-sm font-bold text-fleet-muted hover:bg-slate-50" onClick={() => setShowModal(false)} type="button">Cancel</button>
              <PrimaryButton onClick={() => setShowModal(false)}>Save completion</PrimaryButton>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
