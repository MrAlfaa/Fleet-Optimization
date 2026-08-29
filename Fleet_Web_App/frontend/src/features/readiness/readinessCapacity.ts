export interface ReadinessCapacityInput {
  requiredVehicles: number
  eligibleVehicles: number
  warningVehicles: number
  blockedVehicles: number
}

export interface ReadinessCapacityModel {
  required: number
  eligible: number
  ready: number
  warning: number
  gap: number
  blocked: number
  spare: number
  utilizationPercent: number
}

function normalizeCount(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.max(0, Math.round(value))
}

export function deriveReadinessCapacity(input: ReadinessCapacityInput): ReadinessCapacityModel {
  const required = normalizeCount(input.requiredVehicles)
  const eligible = normalizeCount(input.eligibleVehicles)
  const warning = Math.min(eligible, normalizeCount(input.warningVehicles))
  const blocked = normalizeCount(input.blockedVehicles)

  return {
    required,
    eligible,
    ready: eligible - warning,
    warning,
    gap: Math.max(0, required - eligible),
    blocked,
    spare: Math.max(0, eligible - required),
    utilizationPercent: required === 0 ? 100 : Math.round(Math.min(eligible / required, 1) * 100),
  }
}
