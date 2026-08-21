import '../models/driver_models.dart';
import 'api_client.dart';
import 'driver_service_contracts.dart';
import 'package:uuid/uuid.dart';

class DriverApiService implements DriverDataService {
  DriverApiService({required ApiClient apiClient}) : _apiClient = apiClient;

  final ApiClient _apiClient;
  AssignedVehicle? _lastVehicle;
  DriverRoute? _lastRoute;

  @override
  Future<AssignedVehicle?> getAssignedVehicle() async {
    final data = await _apiClient.get<Object?>('/driver/assigned-vehicle');
    if (data is! Map<String, dynamic>) {
      _lastVehicle = null;
      return null;
    }
    _lastVehicle = AssignedVehicle.fromJson(data);
    return _lastVehicle;
  }

  @override
  Future<DriverRoute?> getTodayRoute() async {
    final data = await _apiClient.get<Object?>('/driver/assigned-route');
    if (data is! Map<String, dynamic>) {
      _lastRoute = null;
      return null;
    }
    final route = DriverRoute.fromAssignedRouteJson(data);
    _lastRoute = route.hasAssignedRoute ? route : null;
    return _lastRoute;
  }

  @override
  Future<List<DriverAlert>> getAlerts() async {
    final data = await _apiClient.get<Object?>('/driver/alerts');
    if (data is! List) {
      return const [];
    }
    return data
        .whereType<Map<String, dynamic>>()
        .map(DriverAlert.fromJson)
        .toList(growable: false);
  }

  @override
  Future<List<TripEvent>> getTripEvents() async {
    final data = await _apiClient.get<Object?>('/driver/trip-events');
    if (data is List) {
      final events = data
          .whereType<Map<String, dynamic>>()
          .map(TripEvent.fromJson)
          .toList(growable: false);
      if (events.isNotEmpty) {
        return events;
      }
    }
    final route = _lastRoute;
    final vehicle = _lastVehicle;
    if (route == null) {
      return const [
        TripEvent(
          time: 'Now',
          title: 'No route assigned',
          description:
              'A dispatched backend route assigned to this driver will appear here.',
          type: AlertSeverity.info,
        ),
      ];
    }
    return [
      TripEvent(
        time: 'Now',
        title: 'Route loaded from backend',
        description:
            '${route.stops.length} stops assigned from ${route.depot}.',
        type: AlertSeverity.info,
      ),
      if (vehicle != null)
        TripEvent(
          time: 'Vehicle',
          title: vehicle.number,
          description: vehicle.riskSummary,
          type: vehicle.riskLevel == 'critical'
              ? AlertSeverity.critical
              : AlertSeverity.warning,
        ),
    ];
  }

  @override
  Future<TripReadiness> getTripReadiness() async {
    final data = await _apiClient.get<Map<String, dynamic>>(
      '/driver/trip-readiness',
    );
    return TripReadiness.fromJson(data);
  }

  @override
  Future<DriverInspectionResult> submitPreTripInspection(
    PreTripInspection inspection,
  ) async {
    final data = await _apiClient.post<Map<String, dynamic>>(
      '/driver/trips/pre-inspection',
      inspection.toJson(),
    );
    return DriverInspectionResult.fromJson(data);
  }

  @override
  Future<DriverInspectionResult> submitPostTripInspection(
    PostTripInspection inspection,
  ) async {
    final data = await _apiClient.post<Map<String, dynamic>>(
      '/driver/trips/post-inspection',
      inspection.toJson(),
    );
    return DriverInspectionResult.fromJson(data);
  }

  @override
  Future<DriverTripSession> startTrip() async {
    final data = await _apiClient.post<Map<String, dynamic>>(
      '/driver/trips/start',
      {},
    );
    return DriverTripSession.fromJson(data);
  }

  @override
  Future<DriverTripSession> endTrip() async {
    final data = await _apiClient.post<Map<String, dynamic>>(
      '/driver/trips/end',
      {},
    );
    return DriverTripSession.fromJson(data);
  }

  @override
  Future<void> sendLocation(DriverLocationUpdate location) async {
    await _apiClient.post<Map<String, dynamic>>(
      '/driver/location',
      location.toJson(),
    );
  }

  @override
  Future<void> updateDeliveryStatus(
    String orderId,
    DeliveryStatus status,
  ) async {
    await _apiClient.patch<Map<String, dynamic>>(
      '/driver/deliveries/$orderId/status',
      {'status': deliveryStatusToBackend(status)},
    );
  }

  @override
  Future<void> markDeliveryIncomplete(
    String orderId, {
    required String reason,
    String? details,
  }) async {
    await _apiClient
        .post<Map<String, dynamic>>('/driver/deliveries/$orderId/incomplete', {
          'reason': reason,
          if (details != null && details.trim().isNotEmpty)
            'details': details.trim(),
          'idempotency_key': const Uuid().v4(),
        });
  }

  @override
  Future<void> acknowledgeAlert(String alertId) async {
    await _apiClient.patch<Map<String, dynamic>>(
      '/driver/alerts/$alertId/acknowledge',
      {},
    );
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
    final body = <String, dynamic>{
      'title': title,
      'message': message,
      'severity': severity,
      'category': category,
    };
    final resolvedVehicleId = vehicleId ?? _lastVehicle?.id;
    final resolvedRouteId = routeId ?? _lastRoute?.id;
    if (resolvedVehicleId != null && resolvedVehicleId.isNotEmpty) {
      body['vehicle_id'] = resolvedVehicleId;
    }
    if (resolvedRouteId != null && resolvedRouteId.isNotEmpty) {
      body['route_id'] = resolvedRouteId;
    }
    await _apiClient.post<Map<String, dynamic>>('/driver/issues', body);
  }
}
