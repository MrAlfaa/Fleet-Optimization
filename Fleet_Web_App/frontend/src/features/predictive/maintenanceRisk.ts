import type { MaintenancePrediction } from '../../types'

export function summarizeLatestFleetRisk(predictions: MaintenancePrediction[]) {
  const latestByVehicle = new Map<string, MaintenancePrediction>()
  for (const prediction of predictions) {
    const current = latestByVehicle.get(prediction.vehicleId)
    if (!current || timestamp(prediction.createdAt) > timestamp(current.createdAt)) latestByVehicle.set(prediction.vehicleId, prediction)
  }
  const latest = [...latestByVehicle.values()]
  return {
    latestByVehicle,
    evaluated: latest.length,
    critical: latest.filter((item) => item.risk === 'critical').length,
    held: latest.filter((item) => item.dispatchHold).length,
    goodQuality: latest.filter((item) => item.dataQuality === 'good').length,
  }
}

function timestamp(value: string) {
  const parsed = Date.parse(value)
  return Number.isFinite(parsed) ? parsed : 0
}
