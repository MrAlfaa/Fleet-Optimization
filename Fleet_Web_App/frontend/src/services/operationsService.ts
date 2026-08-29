import type { Alert, DeliveryOrder, LiveTrip, LiveTripLocation, OperationalBranch, PaginatedResponse, RoutePlan, RouteSet, TripEvent } from '../types'
import { apiClient } from './apiClient'
import { mapAlert, mapDeliveryOrder, mapRoutePlan } from './adapters'

type RecordLike = Record<string, unknown>

function stringValue(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback
}

function numberValue(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : Number(value ?? fallback) || fallback
}

export function mapRouteSet(raw: RecordLike): RouteSet {
  const routes = Array.isArray(raw.routes) ? raw.routes.map((route) => mapRoutePlan(route as RecordLike)) : []
  return {
    routeSetId: stringValue(raw.route_set_id),
    loadPlanId: stringValue(raw.load_plan_id),
    consolidationId: stringValue(raw.consolidation_id),
    optionId: stringValue(raw.option_id),
    deliveryDate: stringValue(raw.delivery_date),
    deliveryPeriod: raw.delivery_period === 'second_half' ? 'second_half' : 'first_half',
    expectedRouteCount: numberValue(raw.expected_route_count, routes.length),
    status: stringValue(raw.status, 'generating') as RouteSet['status'],
    routes,
    error: stringValue(raw.error ?? raw.last_error) || null,
  }
}

export function mapRouteGeometryCoordinates(raw: RecordLike): Array<{ latitude: number; longitude: number }> {
  if (!Array.isArray(raw.coordinates)) return []
  return raw.coordinates.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const point = item as RecordLike
    const latitude = Number(point.latitude)
    const longitude = Number(point.longitude)
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || Math.abs(latitude) > 90 || Math.abs(longitude) > 180) return []
    return [{ latitude, longitude }]
  })
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
  const navigation = raw.navigation && typeof raw.navigation === 'object' ? raw.navigation as RecordLike : {}
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
    navigation: {
      currentStopId: stringValue(navigation.current_stop_id),
      currentParcelCode: stringValue(navigation.current_parcel_code),
      currentCustomerName: stringValue(navigation.current_customer_name),
      status: stringValue(navigation.status, 'idle'),
      startedAt: stringValue(navigation.started_at),
    },
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
  pickup_latitude?: number
  pickup_longitude?: number
  drop_latitude: number
  drop_longitude: number
  pickup_address?: string
  drop_address?: string
  zone_id?: string
  zone_assignment_method?: 'nearest' | 'confirmed' | 'manual_override'
  priority?: string
  scheduled_date?: string
  delivery_date: string
  delivery_period: 'first_half' | 'second_half'
  customer_phone?: string
  parcel_weight?: number
  parcel_volume?: number
  load_profile?: ParcelLoadProfileInput
}

export interface ParcelLoadProfileInput {
  length_cm: number
  width_cm: number
  height_cm: number
  fragile: boolean
  stackable: boolean
  max_stack_weight_kg: number
  loading_orientation_fixed: boolean
  hazardous: boolean
  hazmat_class?: string
  requires_refrigeration: boolean
  temp_min_celsius?: number
  temp_max_celsius?: number
  two_person_lift: boolean
  do_not_tilt: boolean
  service_type: 'door_to_door' | 'collection_point' | 'locker_drop' | 'standard'
}

export const operationsService = {
  async listDeliveries(params: { status?: string; zone_id?: string; priority?: string; delivery_period?: 'first_half' | 'second_half'; load_planning_status?: string; consolidation_id?: string; start_date?: string; end_date?: string; page?: number; limit?: number } = {}): Promise<DeliveryOrder[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/deliveries', {
      query: { page: 1, limit: 100, ...params },
    })
    return data.items.map(mapDeliveryOrder)
  },
  async getOperationalBranch(): Promise<OperationalBranch> {
    const data = await apiClient.get<RecordLike>('/operations/branch')
    const periods = Array.isArray(data.delivery_periods) ? data.delivery_periods : []
    return {
      id: stringValue(data.id, 'colombo_central_branch'),
      name: stringValue(data.name, 'Colombo Central Branch'),
      address: stringValue(data.address, 'Colombo, Sri Lanka'),
      latitude: numberValue(data.latitude, 6.9271),
      longitude: numberValue(data.longitude, 79.8612),
      timezone: stringValue(data.timezone, 'Asia/Colombo'),
      deliveryPeriods: periods.map((value) => {
        const period = value as RecordLike
        return {
          id: period.id === 'second_half' ? 'second_half' as const : 'first_half' as const,
          label: stringValue(period.label),
          start: stringValue(period.start),
          end: stringValue(period.end),
        }
      }),
    }
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
  async getRoutePlan(requestedRouteId?: string): Promise<RoutePlan> {
    if (requestedRouteId) {
      const plan = mapRoutePlan(await apiClient.get<RecordLike>(`/routes/${requestedRouteId}`))
      if (plan.mapPath.length < 2) return { ...plan, geometrySource: 'fallback', geometryCached: false }
      try {
        const geometry = await this.getRouteGeometry(requestedRouteId)
        return geometry.coordinates.length > 1
          ? { ...plan, mapPath: geometry.coordinates, geometrySource: geometry.source === 'osrm' ? 'osrm' : 'fallback', geometryCached: geometry.cached }
          : { ...plan, geometrySource: 'fallback', geometryCached: geometry.cached }
      } catch {
        return { ...plan, geometrySource: 'fallback', geometryCached: false }
      }
    }
    const routes = await apiClient.get<PaginatedResponse<RecordLike>>('/routes', { query: { page: 1, limit: 1, status: 'optimized' } })
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
    const routeId = requestedRouteId || stringValue(routes.items[0].id)
    if (!routeId) return mapRoutePlan(routes.items[0])
    const plan = mapRoutePlan(await apiClient.get<RecordLike>(`/routes/${routeId}`))
    if (plan.mapPath.length < 2) return { ...plan, geometrySource: 'fallback', geometryCached: false }
    try {
      const geometry = await this.getRouteGeometry(routeId)
      return geometry.coordinates.length > 1
        ? { ...plan, mapPath: geometry.coordinates, geometrySource: geometry.source === 'osrm' ? 'osrm' : 'fallback', geometryCached: geometry.cached }
        : { ...plan, geometrySource: 'fallback', geometryCached: geometry.cached }
    } catch {
      return { ...plan, geometrySource: 'fallback', geometryCached: false }
    }
  },
  async getRouteGeometry(routeId: string): Promise<{ source: 'osrm' | 'fallback'; cached: boolean; coordinates: Array<{ latitude: number; longitude: number }> }> {
    const data = await apiClient.get<RecordLike>(`/routes/${routeId}/geometry`)
    return {
      source: data.geometry_source === 'osrm' ? 'osrm' : 'fallback',
      cached: data.cached === true,
      coordinates: mapRouteGeometryCoordinates(data),
    }
  },
  async listRoutes(params: { status?: string; page?: number; limit?: number } = {}): Promise<RoutePlan[]> {
    const data = await apiClient.get<PaginatedResponse<RecordLike>>('/routes', { query: { page: 1, limit: 20, ...params } })
    return data.items.map(mapRoutePlan)
  },
  async optimizeRoute(payload: RecordLike): Promise<RoutePlan> {
    const result = await apiClient.post<RecordLike>('/routes/optimize', payload)
    const routeId = stringValue(result.route_id)
    return routeId ? this.getRoutePlan(routeId) : mapRoutePlan({ ...result, id: result.route_id })
  },
  async dispatchRoute(routeId: string, payload: RecordLike = {}): Promise<RoutePlan> {
    return mapRoutePlan(await apiClient.post<RecordLike>(`/routes/${routeId}/dispatch`, payload))
  },
  async createRouteSet(loadPlanId: string): Promise<RouteSet> {
    return mapRouteSet(await apiClient.post<RecordLike>(`/route-sets/from-load-plan/${loadPlanId}`, {}))
  },
  async getRouteSet(routeSetId: string): Promise<RouteSet> {
    const routeSet = mapRouteSet(await apiClient.get<RecordLike>(`/route-sets/${routeSetId}`))
    const routes = await Promise.all(routeSet.routes.map(async (route) => {
      try {
        return await this.getRoutePlan(route.id)
      } catch {
        return route
      }
    }))
    return { ...routeSet, routes }
  },
  async approveRouteSet(routeSetId: string): Promise<RouteSet> {
    return mapRouteSet(await apiClient.post<RecordLike>(`/route-sets/${routeSetId}/approve`, {}))
  },
  async assignRouteDriver(routeSetId: string, routeId: string, driverId: string): Promise<RouteSet> {
    return mapRouteSet(await apiClient.post<RecordLike>(`/route-sets/${routeSetId}/routes/${routeId}/assign-driver`, { driver_id: driverId }))
  },
  async dispatchRouteSet(routeSetId: string): Promise<RouteSet> {
    return mapRouteSet(await apiClient.post<RecordLike>(`/route-sets/${routeSetId}/dispatch`, {}))
  },
  async getRouteDashboardSummary(): Promise<RecordLike> {
    return apiClient.get<RecordLike>('/routes/dashboard-summary')
  },
  async listLiveTrips(): Promise<LiveTrip[]> {
    const data = await apiClient.get<{ items?: RecordLike[] }>('/live-trips')
    return (data.items ?? []).map(mapLiveTrip)
  },
  async getLiveTripLocations(routeId: string): Promise<LiveTripLocation[]> {
    const data = await apiClient.get<{ items?: RecordLike[] } | RecordLike[]>(`/live-trips/${routeId}/locations`)
    const items = Array.isArray(data) ? data : (data.items ?? [])
    return items.map(mapLiveTripLocation)
  },
  async getLiveTripEvents(routeId: string): Promise<TripEvent[]> {
    const data = await apiClient.get<{ items?: RecordLike[] } | RecordLike[]>(`/live-trips/${routeId}/events`)
    const items = Array.isArray(data) ? data : (data.items ?? [])
    return items
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
