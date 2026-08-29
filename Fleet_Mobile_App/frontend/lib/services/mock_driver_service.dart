import '../models/driver_models.dart';
import 'driver_service_contracts.dart';

class MockDriverService implements DriverDataService {
  DriverRoute _route = const DriverRoute(
    id: 'route-7a',
    title: 'Route 7A - Colombo East',
    depot: 'Port 4 Distribution Hub',
    depotLatitude: 6.9271,
    depotLongitude: 79.8612,
    totalDistanceKm: 86.4,
    eta: '14:30',
    stops: [
      RouteStop(
        id: 'stop-1',
        parcelCode: 'QA-PARCEL-001',
        customerPhone: '0771234567',
        parcelWeightKg: 12.5,
        lengthCm: 60,
        widthCm: 40,
        heightCm: 35,
        handling: ['Fragile', 'Do not tilt'],
        sequence: 1,
        customer: 'District Center Alpha',
        address: '220 Lake Drive, Colombo Central',
        zone: 'Colombo Central',
        eta: '09:20',
        priority: 'Critical',
        latitude: 6.9271,
        longitude: 79.8612,
        status: DeliveryStatus.pending,
      ),
      RouteStop(
        id: 'stop-2',
        sequence: 2,
        customer: 'Nugegoda Medical Stores',
        address: '45 High Level Road, Nugegoda',
        zone: 'Nugegoda',
        eta: '10:40',
        priority: 'High',
        latitude: 6.8649,
        longitude: 79.8997,
        status: DeliveryStatus.pending,
      ),
      RouteStop(
        id: 'stop-3',
        sequence: 3,
        customer: 'Malabe Fulfillment Point',
        address: '310 IT Park Avenue, Malabe',
        zone: 'Malabe',
        eta: '12:15',
        priority: 'Standard',
        latitude: 6.9061,
        longitude: 79.9696,
        status: DeliveryStatus.pending,
      ),
      RouteStop(
        id: 'stop-4',
        sequence: 4,
        customer: 'Kaduwela Retail Hub',
        address: '88 Riverside Road, Kaduwela',
        zone: 'Kaduwela',
        eta: '13:45',
        priority: 'Standard',
        latitude: 6.9358,
        longitude: 79.9842,
        status: DeliveryStatus.pending,
      ),
    ],
  );

  List<DriverAlert> _alerts = const [
    DriverAlert(
      id: 'alert-1',
      title: 'Maintenance Risk Warning',
      message:
          'TRK-492 brake risk remains medium. Complete route and report abnormal vibration.',
      category: 'Maintenance',
      severity: AlertSeverity.warning,
      timestamp: '08:10 AM',
      acknowledged: false,
    ),
    DriverAlert(
      id: 'alert-2',
      title: 'Weather Watch',
      message:
          'Rain expected near Malabe after 12:00. Planner recommends keeping Route 7A order.',
      category: 'Weather',
      severity: AlertSeverity.info,
      timestamp: '08:25 AM',
      acknowledged: false,
    ),
    DriverAlert(
      id: 'alert-3',
      title: 'Priority Delivery',
      message: 'District Center Alpha must be completed before 09:45.',
      category: 'Route',
      severity: AlertSeverity.critical,
      timestamp: '08:32 AM',
      acknowledged: false,
    ),
  ];

  @override
  Future<AssignedVehicle?> getAssignedVehicle() async {
    return const AssignedVehicle(
      id: 'veh-492',
      number: 'TRK-492',
      model: 'Volvo VNL',
      type: 'Heavy Truck',
      mileage: 142500,
      riskLevel: 'medium',
      riskSummary:
          'Brake pads show elevated wear. Avoid extended high-load dispatch.',
      modelStatus: 'Maintenance monitoring active',
      category: 'truck',
      fuelType: 'diesel',
    );
  }

  @override
  Future<DriverRoute?> getTodayRoute() async {
    return _route;
  }

  @override
  Future<RouteGeometry> getRouteGeometry(String routeId) async {
    return RouteGeometry.fallbackFor(_route);
  }

  @override
  Future<List<DriverAlert>> getAlerts() async {
    return _alerts;
  }

  @override
  Future<List<TripEvent>> getTripEvents() async {
    return const [
      TripEvent(
        time: '08:00',
        title: 'Pre-trip inspection cleared',
        description:
            'Vehicle condition accepted with medium brake-risk notice.',
        type: AlertSeverity.info,
      ),
      TripEvent(
        time: '08:15',
        title: 'Route assigned',
        description: 'Route 7A synced from planner dashboard placeholder data.',
        type: AlertSeverity.info,
      ),
    ];
  }

  @override
  Future<TripReadiness> getTripReadiness() async {
    return const TripReadiness(
      canStart: true,
      vehicleRegistration: 'WP CAA-4920',
      vehicleCategory: 'electric_van',
      vehicleStatus: 'warning',
      maintenanceRisk: 'medium',
      routeDelayRisk: 'medium',
      demandLevels: ['high'],
      routeDistanceKm: 86.4,
      warnings: ['Maintenance monitoring required during this route'],
      blockingReasons: [],
      reviewStatus: 'not_required',
    );
  }

  @override
  Future<DriverInspectionResult> submitPreTripInspection(
    PreTripInspection inspection,
  ) async {
    return const DriverInspectionResult(
      id: 'mock-pre',
      safeToOperate: true,
      blockingReasons: [],
    );
  }

  @override
  Future<DriverInspectionResult> submitPostTripInspection(
    PostTripInspection inspection,
  ) async {
    return DriverInspectionResult(
      id: 'mock-post',
      safeToOperate: true,
      blockingReasons: const [],
      tripDistanceKm: inspection.endingOdometer - 42000,
    );
  }

  @override
  Future<DriverTripSession> startTrip() async {
    return const DriverTripSession(
      id: 'mock-trip-session',
      routeId: 'route-7a',
      routeCode: 'ROUTE-MOCK-7A',
      status: 'active',
      startedAt: 'Now',
    );
  }

  @override
  Future<DriverTripSession> endTrip() async {
    return const DriverTripSession(
      id: 'mock-trip-session',
      routeId: 'route-7a',
      routeCode: 'ROUTE-MOCK-7A',
      status: 'completed',
      endedAt: 'Ended',
    );
  }

  @override
  Future<void> sendLocation(DriverLocationUpdate location) async {}

  @override
  Future<void> updateDeliveryStatus(
    String orderId,
    DeliveryStatus status,
  ) async {
    final stops = _route.stops
        .map(
          (stop) => stop.id == orderId ? stop.copyWith(status: status) : stop,
        )
        .toList(growable: false);
    _route = _route.copyWith(stops: stops);
  }

  @override
  Future<void> markDeliveryIncomplete(
    String orderId, {
    required String reason,
    String? details,
  }) async {
    await updateDeliveryStatus(orderId, DeliveryStatus.failed);
  }

  @override
  Future<void> acknowledgeAlert(String alertId) async {
    _alerts = _alerts
        .map(
          (alert) =>
              alert.id == alertId ? alert.copyWith(acknowledged: true) : alert,
        )
        .toList(growable: false);
  }

  @override
  Future<void> submitIssue({
    required String title,
    required String message,
    String severity = 'warning',
    String? vehicleId,
    String? routeId,
    String category = 'other',
  }) async {
    _alerts = [
      DriverAlert(
        id: 'mock-driver-issue',
        title: title,
        message: message,
        category: 'driver',
        severity: severity == 'critical'
            ? AlertSeverity.critical
            : AlertSeverity.warning,
        timestamp: 'Now',
        acknowledged: false,
      ),
      ..._alerts,
    ];
  }
}
