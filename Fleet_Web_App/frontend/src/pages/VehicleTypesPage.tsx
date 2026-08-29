import { Box, Plus, ShieldCheck, Snowflake, Truck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, DataTable, ErrorState, LoadingState, PageHeader, SecondaryButton, StatusBadge } from '../components/UI'
import type { LoadVehicleType } from '../features/loadOptimization/types'
import { loadOptimizationService } from '../services/loadOptimizationService'

export function VehicleTypesPage() {
  const navigate = useNavigate()
  const [types, setTypes] = useState<LoadVehicleType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadTypes = async () => {
    setLoading(true)
    setError('')
    try { setTypes((await loadOptimizationService.vehicleTypes()).items) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to load vehicle types') }
    finally { setLoading(false) }
  }
  useEffect(() => {
    queueMicrotask(() => { void loadTypes() })
  }, [])
  if (loading) return <LoadingState label="Loading optimizer vehicle types" />
  if (error) return <ErrorState message={error} onRetry={loadTypes} />

  return <div className="space-y-5">
    <PageHeader title="Vehicle Types" description="Reference capacity profiles used to create virtual loads and match registered fleet vehicles." action={<SecondaryButton onClick={() => navigate('/vehicles')}><Plus className="h-4 w-4" /> Register physical vehicle</SecondaryButton>} />
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><TypeMetric label="Optimizer profiles" value={String(types.length)} icon={Box} /><TypeMetric label="Registered vehicles" value={String(types.reduce((sum, item) => sum + item.registered_vehicle_count, 0))} icon={Truck} /><TypeMetric label="Active matches" value={String(types.reduce((sum, item) => sum + item.active_vehicle_count, 0))} icon={ShieldCheck} /><TypeMetric label="Special profiles" value={String(types.filter((item) => item.is_refrigerated || item.is_hazmat_certified).length)} icon={Snowflake} /></div>
    <Card title="Optimizer vehicle catalogue">
      <DataTable headers={['Profile', 'Category', 'Payload', 'Cargo bay', 'Parcels / layers', 'Capabilities', 'Registered', 'Active']}>
        {types.map((item) => <tr key={item.code}><td className="px-5 py-4"><div className="font-black">{item.label}</div><div className="text-xs font-semibold text-fleet-muted">{item.code}</div></td><td className="px-5 py-4 capitalize">{item.category}</td><td className="px-5 py-4">{item.capacity_kg.toLocaleString()} kg<br/><span className="text-xs text-fleet-muted">{item.capacity_m3} m³</span></td><td className="px-5 py-4">{item.cargo_length_cm} × {item.cargo_width_cm} × {item.cargo_height_cm} cm</td><td className="px-5 py-4">{item.max_parcels} parcels<br/><span className="text-xs text-fleet-muted">{item.max_stack_layers} layers</span></td><td className="px-5 py-4"><div className="flex flex-wrap gap-1">{item.is_refrigerated && <StatusBadge tone="blue">Refrigerated</StatusBadge>}{item.is_hazmat_certified && <StatusBadge tone="amber">Hazmat</StatusBadge>}{!item.is_refrigerated && !item.is_hazmat_certified && <StatusBadge tone="slate">Standard</StatusBadge>}</div></td><td className="px-5 py-4 font-bold">{item.registered_vehicle_count}</td><td className="px-5 py-4"><StatusBadge tone={item.active_vehicle_count ? 'green' : 'slate'}>{item.active_vehicle_count}</StatusBadge></td></tr>)}
      </DataTable>
    </Card>
  </div>
}

function TypeMetric({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Box }) { return <div className="flex items-center justify-between rounded-lg border border-fleet-line bg-white p-4 shadow-card"><div><div className="text-xs font-bold uppercase text-fleet-muted">{label}</div><div className="mt-2 text-2xl font-black">{value}</div></div><Icon className="h-6 w-6 text-blue-600" /></div> }
