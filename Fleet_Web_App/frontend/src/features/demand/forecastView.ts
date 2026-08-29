import type { DemandForecast, DemandLevel, DemandZone, OperationalZoneOption } from '../../types'


export interface DemandTrendPoint {
  date: string
  label: string
  actual: number | null
  actualAvailable: boolean
  predicted: number
}

function dateKey(value: string | undefined) {
  return value?.slice(0, 10) ?? ''
}

function dateLabel(value: string) {
  const parsed = new Date(`${value}T00:00:00Z`)
  return Number.isNaN(parsed.getTime())
    ? value
    : parsed.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

export function forecastDates(items: DemandForecast[]) {
  return [...new Set(items.map((item) => dateKey(item.date)).filter(Boolean))].sort()
}

export function limitForecastDates(items: DemandForecast[], horizonDays: number) {
  const visibleDates = new Set(forecastDates(items).slice(0, horizonDays))
  return items.filter((item) => item.date && visibleDates.has(dateKey(item.date)))
}

export function aggregateForecastTrend(items: DemandForecast[]): DemandTrendPoint[] {
  const grouped = new Map<string, DemandTrendPoint>()
  for (const item of items) {
    const date = dateKey(item.date)
    if (!date) continue
    const current = grouped.get(date) ?? { date, label: dateLabel(date), actual: null, actualAvailable: false, predicted: 0 }
    current.predicted += item.predictedVolume
    if (item.actualAvailable) {
      current.actual = (current.actual ?? 0) + item.currentVolume
      current.actualAvailable = true
    }
    grouped.set(date, current)
  }
  return [...grouped.values()].sort((left, right) => left.date.localeCompare(right.date))
}

function riskFromDemandLevel(level: DemandLevel) {
  return level === 'very_high' ? 'critical' : level
}

export function buildZoneSnapshots(
  zones: OperationalZoneOption[],
  forecasts: DemandForecast[],
  selectedDate: string,
): DemandZone[] {
  const byZone = new Map(
    forecasts
      .filter((item) => dateKey(item.date) === selectedDate && item.zoneId)
      .map((item) => [item.zoneId as string, item]),
  )
  return zones.map((zone) => {
    const forecast = byZone.get(zone.id)
    const demandLevel = forecast?.demandLevel ?? 'low'
    return {
      id: zone.id,
      name: zone.name,
      predicted: forecast?.predictedVolume ?? 0,
      actual: forecast?.currentVolume ?? 0,
      actualAvailable: forecast?.actualAvailable ?? false,
      overloadScore: forecast?.predictedVolume ?? 0,
      risk: riskFromDemandLevel(demandLevel),
      demandLevel,
      requiredVehicles: forecast?.requiredVehicles ?? 0,
      varianceOrders: forecast?.varianceOrders ?? null,
    }
  })
}
