import { Navigate, useParams } from 'react-router-dom'

export function VehicleMaintenancePage() {
  const { vehicleId = '' } = useParams()
  return <Navigate replace to={`/vehicles/${encodeURIComponent(vehicleId)}?tab=maintenance`} />
}
