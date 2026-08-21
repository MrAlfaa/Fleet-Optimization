import type { Alert, DeliveryOrder, LiveTrip, LiveTripLocation, PaginatedResponse, RoutePlan, TripEvent } from '../types'
import { apiClient } from './apiClient'
import { mapAlert, mapDeliveryOrder, mapRoutePlan } from './adapters'

type RecordLike = Record<string, unknown>

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback
}

function numberValue(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : Number(value ?? fallback) || fallback
}

function mapTripEvent(raw: unknown, fallbackId: string): TripEvent | null {
  if (!raw || typeof raw !== 'object') return null
  const event = raw as RecordLike
  const severity = stringValue(event.severity, 'info')
  return {
    id: stringValue(event.id, fallbackId),
    time: stringValue(event.created_at, 'Recent'),
    title: stringValue(event.title, 'Trip event'),
    description: stringValue(event.description, stringValue(event.event_type, 'Driver route event')),
    severity: severity === 'critical' || severity === 'warning' ? severity : 'info',
  }
}

function mapLiveTrip(raw: RecordLike): LiveTrip {
  const latestLocation = raw.latest_location && typeof raw.latest_location === 'object' ? raw.latest_location as RecordLike : null
  const progress = raw.progress && typeof raw.progress === 'object' ? raw.progress as RecordLike : {}
  const routeId = stringValue(raw.route_id)
  return {
    routeId,
    routeCode: stringValue(raw.route_code, 'Route'),
    routeName: stringValue(raw.route_name, stringValue(raw.route_code, 'Live route')),
    driverName: stringValue(raw.driver_name, 'Unassigned driver'),
    vehicleCode: stringValue(raw.vehicle_code, 'Unassigned vehicle'),
    tripStatus: stringValue(raw.trip_status, 'inactive'),
    routeStatus: stringValue(raw.route_status, 'unknown'),
    latestLocation: latestLocation ? {
      latitude: numberValue(latestLocation.latitude),
      longitude: numberValue(latestLocation.longitude),
      recordedAt: stringValue(latestLocation.recorded_at ?? latestLocation.created_at, 'No location yet'),
    } : null,
    progress: {
      totalStops: numberValue(progress.total_stops),
      completedStops: numberValue(progress.completed_stops),
    },
    latestEvent: mapTripEvent(raw.latest_event, routeId),
  }
}

function mapLiveTripLocation(raw: RecordLike): LiveTripLocation {
  return {
    id: stringValue(raw.id),
    latitude: numberValue(raw.latitude),
    longitude: numberValue(raw.longitude),
    recordedAt: stringValue(raw.recorded_at ?? raw.created_at, 'No timestamp'),
  }
}

export interface DeliveryCreatePayload {
  order_code?: string
  customer_name?: string
  pickup_latitude: number
  pickup_longitude: number
  drop_latitude: number
  drop_longitude: number
  pickup_address?: string
  drop_address?: string
  zone_id?: string
  zone_assignment_method?: 'nearest' | 'confirmed' | 'manual_override'
  priority?: string
  scheduled_date?: string
}

export const operationsService = {
  async listDeliveries(params: { status?: string; zone_id?: string; priority?: string; start_date?: string; end_date?: string; page?: number; limit?: number } = {}): Promise<DeliveryOrder[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/deliveries', {
      query: { page: 1, limit: 100, ...params },
    })
    return data.items.map(mapDeliveryOrder)
  },
  async createDelivery(payload: DeliveryCreatePayload): Promise<DeliveryOrder> {
    return mapDeliveryOrder(await apiClient.post<RecordLike>('/deliveries', payload))
  },
  async updateDelivery(orderId: string, payload: Partial<DeliveryCreatePayload>): Promise<DeliveryOrder> {
    return mapDeliveryOrder(await apiClient.put<RecordLike>(`/deliveries/${orderId}`, payload))
  },
  async cancelDelivery(orderId: string, reason: string): Promise<DeliveryOrder> {
    return mapDeliveryOrder(await apiClient.post<RecordLike>(`/deliveries/${orderId}/cancel`, { reason }))
  },
  async cancelRoute(routeId: string): Promise<RoutePlan> {
    return mapRoutePlan(await apiClient.post<RecordLike>(`/routes/${routeId}/cancel`, {}))
  },
  async updateDeliveryStatus(orderId: string, status: string): Promise<DeliveryOrder> {
    return mapDeliveryOrder(await apiClient.patch<RecordLike>(`/deliveries/${orderId}/status`, { status }))
  },
  async getRoutePlan(): Promise<RoutePlan> {
    const routes = await apiClient.get<PaginatedResponse<RecordLike>>('/routes', { query: { page: 1, limit: 1 } })
    if (!routes.items[0]) {
      return {
        id: 'no-route',
        vehicle: 'Unassigned',
        driver: 'Unassigned',
        distance: '0 km',
        eta: '0 min',
        capacityUse: 0,
        stops: [],
        mapPath: [],
        warning: 'No route plan has been saved yet.',
      }
    }
    const routeId = stringValue(routes.items[0].id)
    if (!routeId) return mapRoutePlan(routes.items[0])
    return mapRoutePlan(await apiClient.get<RecordLike>(`/routes/${routeId}`))
  },
  async listRoutes(params: { status?: string; page?: number; limit?: number } = {}): Promise<RoutePlan[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/routes', { query: { page: 1, limit: 20, ...params } })
    return data.items.map(mapRoutePlan)
  },
  async optimizeRoute(payload: RecordLike): Promise<RecordLike> {
    return apiClient.post<RecordLike>('/routes/optimize', payload)
  },
  async dispatchRoute(routeId: string, payload: RecordLike = {}): Promise<RoutePlan> {
    return mapRoutePlan(await apiClient.post<RecordLike>(`/routes/${routeId}/dispatch`, payload))
  },
  async getRouteDashboardSummary(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/routes/dashboard-summary')
  },
  async listLiveTrips(): Promise<LiveTrip[]> {
    const data = await apiClient.get<{ items?: RecordLike[] }>('/live-trips')
    return (data.items ?? []).map(mapLiveTrip)
  },
  async getLiveTripLocations(routeId: string): Promise<LiveTripLocation[]> {
    const data = await apiClient.get<{ items?: RecordLike[] }>(`/live-trips/${routeId}/locations`)
    return (data.items ?? []).map(mapLiveTripLocation)
  },
  async getLiveTripEvents(routeId: string): Promise<TripEvent[]> {
    const data = await apiClient.get<{ items?: RecordLike[] }>(`/live-trips/${routeId}/events`)
    return (data.items ?? [])
      .map((event, index) => mapTripEvent(event, `${routeId}-event-${index}`))
      .filter((event): event is TripEvent => event !== null)
  },
  async getRouteModelStatus(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/routes/model/status')
  },
  async getRouteTrend(): Promise<Array<{ day: string; actual: number; planned: number }>> {
    const summary = await this.getRouteDashboardSummary()
    return [
      { day: 'Routes', actual: Number(summary.active_routes_count ?? 0), planned: Number(summary.optimized_routes_count ?? 0) },
      { day: 'Dispatch', actual: Number(summary.dispatched_routes_count ?? 0), planned: Number(summary.total_route_plans ?? 0) },
    ]
  },
  async listTripEvents(): Promise<TripEvent[]> {
    const trips = await this.listLiveTrips()
    return trips
      .map((trip) => trip.latestEvent)
      .filter((event): event is TripEvent => event !== null)
  },
  async listAlerts(): Promise<Alert[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/alerts', { query: { page: 1, limit: 20 } })
    return data.items.map(mapAlert)
  },
}
