import { alerts, deliveries, routePlan, routeTrend, tripEvents } from '../data/mockData'

export const operationsService = {
  listDeliveries: () => Promise.resolve(deliveries),
  getRoutePlan: () => Promise.resolve(routePlan),
  getRouteTrend: () => Promise.resolve(routeTrend),
  listTripEvents: () => Promise.resolve(tripEvents),
  listAlerts: () => Promise.resolve(alerts),
}
