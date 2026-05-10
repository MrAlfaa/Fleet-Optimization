import { demandForecasts, demandTrend, demandZones } from '../data/mockData'

export const forecastService = {
  listZones: () => Promise.resolve(demandZones),
  listForecasts: () => Promise.resolve(demandForecasts),
  getTrend: () => Promise.resolve(demandTrend),
  getModelStatus: () => Promise.resolve('Placeholder moving average' as const),
}
