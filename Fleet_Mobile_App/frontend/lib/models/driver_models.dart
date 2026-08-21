enum DeliveryStatus { pending, arrived, delivered, failed }

enum AlertSeverity { info, warning, critical }

String _stringValue(Object? value, String fallback) {
  if (value == null) {
    return fallback;
  }
  final text = value.toString().trim();
  return text.isEmpty ? fallback : text;
}

double _doubleValue(Object? value, double fallback) {
  if (value is num) {
    return value.toDouble();
  }
  return double.tryParse(value?.toString() ?? '') ?? fallback;
}

int _intValue(Object? value, int fallback) {
  if (value is num) {
    return value.round();
  }
  return int.tryParse(value?.toString() ?? '') ?? fallback;
}

DeliveryStatus deliveryStatusFromBackend(Object? value) {
  return switch (_stringValue(value, 'pending').toLowerCase()) {
    'arrived' => DeliveryStatus.arrived,
    'delivered' => DeliveryStatus.delivered,
    'failed' || 'cancelled' => DeliveryStatus.failed,
    _ => DeliveryStatus.pending,
  };
}

String deliveryStatusToBackend(DeliveryStatus status) {
  return switch (status) {
    DeliveryStatus.pending => 'in_route',
    DeliveryStatus.arrived => 'arrived',
    DeliveryStatus.delivered => 'delivered',
    DeliveryStatus.failed => 'failed',
  };
}

AlertSeverity alertSeverityFromBackend(Object? value) {
  return switch (_stringValue(value, 'info').toLowerCase()) {
    'critical' || 'high' => AlertSeverity.critical,
    'warning' || 'medium' => AlertSeverity.warning,
    _ => AlertSeverity.info,
  };
}

class DriverUser {
  const DriverUser({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
    this.username = '',
  });

  final String id;
  final String name;
  final String email;
  final String role;
  final String username;

  factory DriverUser.fromJson(Map<String, dynamic> json) {
    return DriverUser(
      id: _stringValue(json['id'], ''),
      name: _stringValue(json['full_name'] ?? json['name'], 'Driver'),
      email: _stringValue(json['email'], ''),
      role: _stringValue(json['role'], 'driver'),
      username: _stringValue(json['username'], ''),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'full_name': name,
      'email': email,
      'role': role,
      'username': username,
    };
  }
}

class AssignedVehicle {
  const AssignedVehicle({
    required this.id,
    required this.number,
    required this.model,
    required this.type,
    required this.mileage,
    required this.riskLevel,
    required this.riskSummary,
    required this.modelStatus,
  });

  final String id;
  final String number;
  final String model;
  final String type;
  final int mileage;
  final String riskLevel;
  final String riskSummary;
  final String modelStatus;

  factory AssignedVehicle.empty() {
    return const AssignedVehicle(
      id: '',
      number: 'No assigned vehicle',
      model: 'Awaiting dispatch',
      type: 'EV',
      mileage: 0,
      riskLevel: 'unknown',
      riskSummary:
          'No vehicle is currently assigned to this driver. Dispatch a route from the web dashboard to load vehicle risk details.',
      modelStatus: 'No assignment',
    );
  }

  factory AssignedVehicle.fromJson(Map<String, dynamic> json) {
    final brand = _stringValue(json['brand'], '');
    final model = _stringValue(json['model'], 'Assigned EV');
    final displayModel = brand.isEmpty ? model : '$brand $model';
    final healthStatus = _stringValue(json['health_status'], 'unknown');
    return AssignedVehicle(
      id: _stringValue(json['id'], ''),
      number: _stringValue(
        json['registration_number'] ?? json['vehicle_code'],
        'Assigned vehicle',
      ),
      model: displayModel,
      type: _stringValue(json['vehicle_type'], 'EV'),
      mileage: _intValue(json['current_mileage'], 0),
      riskLevel: healthStatus,
      riskSummary: _stringValue(
        json['risk_summary'],
        'Vehicle assignment is loaded from the backend.',
      ),
      modelStatus: _stringValue(json['model_status'], healthStatus),
    );
  }
}

class RouteStop {
  const RouteStop({
    required this.id,
    required this.sequence,
    required this.customer,
    required this.address,
    required this.zone,
    required this.eta,
    required this.priority,
    required this.latitude,
    required this.longitude,
    required this.status,
  });

  final String id;
  final int sequence;
  final String customer;
  final String address;
  final String zone;
  final String eta;
  final String priority;
  final double latitude;
  final double longitude;
  final DeliveryStatus status;

  RouteStop copyWith({DeliveryStatus? status}) {
    return RouteStop(
      id: id,
      sequence: sequence,
      customer: customer,
      address: address,
      zone: zone,
      eta: eta,
      priority: priority,
      latitude: latitude,
      longitude: longitude,
      status: status ?? this.status,
    );
  }

  factory RouteStop.fromJson(Map<String, dynamic> json) {
    return RouteStop(
      id: _stringValue(json['id'], ''),
      sequence: _intValue(json['sequence'], 0),
      customer: _stringValue(json['customer_name'], 'Delivery stop'),
      address: _stringValue(json['drop_address'], 'No address provided'),
      zone: _stringValue(json['zone_id'], 'Unassigned zone'),
      eta: _stringValue(json['eta'], '--'),
      priority: _stringValue(json['priority'], 'medium'),
      latitude: _doubleValue(json['drop_latitude'], 0),
      longitude: _doubleValue(json['drop_longitude'], 0),
      status: deliveryStatusFromBackend(json['delivery_status']),
    );
  }
}

class DriverRoute {
  const DriverRoute({
    required this.id,
    required this.title,
    required this.depot,
    required this.depotLatitude,
    required this.depotLongitude,
    required this.totalDistanceKm,
    required this.eta,
    required this.stops,
  });

  final String id;
  final String title;
  final String depot;
  final double depotLatitude;
  final double depotLongitude;
  final double totalDistanceKm;
  final String eta;
  final List<RouteStop> stops;

  int get completedStops =>
      stops.where((stop) => stop.status == DeliveryStatus.delivered).length;

  RouteStop? get nextStop {
    for (final stop in stops) {
      if (stop.status != DeliveryStatus.delivered &&
          stop.status != DeliveryStatus.failed) {
        return stop;
      }
    }
    return null;
  }

  bool get hasAssignedRoute => id.isNotEmpty && stops.isNotEmpty;

  DriverRoute copyWith({List<RouteStop>? stops}) {
    return DriverRoute(
      id: id,
      title: title,
      depot: depot,
      depotLatitude: depotLatitude,
      depotLongitude: depotLongitude,
      totalDistanceKm: totalDistanceKm,
      eta: eta,
      stops: stops ?? this.stops,
    );
  }

  factory DriverRoute.empty() {
    return const DriverRoute(
      id: '',
      title: 'No assigned route',
      depot: 'Awaiting dispatch',
      depotLatitude: 0,
      depotLongitude: 0,
      totalDistanceKm: 0,
      eta: '--',
      stops: [],
    );
  }

  factory DriverRoute.fromAssignedRouteJson(Map<String, dynamic> json) {
    final route = json['route'];
    if (route is! Map<String, dynamic>) {
      return DriverRoute.empty();
    }
    final stopsJson = json['stops'];
    final stops = stopsJson is List
        ? stopsJson
              .whereType<Map<String, dynamic>>()
              .map(RouteStop.fromJson)
              .toList(growable: false)
        : <RouteStop>[];
    final etaMinutes = _doubleValue(route['total_predicted_eta_minutes'], 0);
    return DriverRoute(
      id: _stringValue(route['id'], ''),
      title: _stringValue(
        route['route_name'] ?? route['route_code'],
        'Assigned route',
      ),
      depot: _stringValue(route['depot_name'], 'Depot'),
      depotLatitude: _doubleValue(route['depot_latitude'], 0),
      depotLongitude: _doubleValue(route['depot_longitude'], 0),
      totalDistanceKm: _doubleValue(route['total_distance_km'], 0),
      eta: etaMinutes > 0 ? '${etaMinutes.round()} min' : '--',
      stops: stops,
    );
  }
}

class PreTripInspection {
  const PreTripInspection({
    required this.odometer,
    required this.batterySoc,
    required this.tireCondition,
    required this.brakeCondition,
    required this.chargingCondition,
    required this.vehicleDamage,
    required this.dashboardWarning,
    required this.unusualNoise,
    required this.unusualVibration,
    this.notes,
  });

  final double odometer;
  final double batterySoc;
  final String tireCondition;
  final String brakeCondition;
  final String chargingCondition;
  final String vehicleDamage;
  final String dashboardWarning;
  final String unusualNoise;
  final String unusualVibration;
  final String? notes;

  Map<String, dynamic> toJson() => {
    'odometer': odometer,
    'battery_soc': batterySoc,
    'tire_condition': tireCondition,
    'brake_condition': brakeCondition,
    'charging_condition': chargingCondition,
    'vehicle_damage': vehicleDamage,
    'dashboard_warning': dashboardWarning,
    'unusual_noise': unusualNoise,
    'unusual_vibration': unusualVibration,
    if (notes != null && notes!.trim().isNotEmpty) 'notes': notes!.trim(),
  };
}

class PostTripInspection {
  const PostTripInspection({
    required this.endingOdometer,
    required this.endingBatterySoc,
    required this.tireConditionChange,
    required this.brakeConditionChange,
    required this.chargingProblem,
    required this.vehicleDamage,
    required this.dashboardWarning,
    required this.unusualNoise,
    required this.unusualVibration,
    this.notes,
  });

  final double endingOdometer;
  final double endingBatterySoc;
  final String tireConditionChange;
  final String brakeConditionChange;
  final String chargingProblem;
  final String vehicleDamage;
  final String dashboardWarning;
  final String unusualNoise;
  final String unusualVibration;
  final String? notes;

  Map<String, dynamic> toJson() => {
    'ending_odometer': endingOdometer,
    'ending_battery_soc': endingBatterySoc,
    'tire_condition_change': tireConditionChange,
    'brake_condition_change': brakeConditionChange,
    'charging_problem': chargingProblem,
    'vehicle_damage': vehicleDamage,
    'dashboard_warning': dashboardWarning,
    'unusual_noise': unusualNoise,
    'unusual_vibration': unusualVibration,
    if (notes != null && notes!.trim().isNotEmpty) 'notes': notes!.trim(),
  };
}

class DriverInspectionResult {
  const DriverInspectionResult({
    required this.id,
    required this.safeToOperate,
    required this.blockingReasons,
    this.predictionRisk,
    this.predictionError,
    this.tripDistanceKm,
    this.batterySocUsed,
  });

  final String id;
  final bool safeToOperate;
  final List<String> blockingReasons;
  final String? predictionRisk;
  final String? predictionError;
  final double? tripDistanceKm;
  final double? batterySocUsed;

  factory DriverInspectionResult.fromJson(Map<String, dynamic> json) {
    final reasons = json['blocking_reasons'];
    return DriverInspectionResult(
      id: _stringValue(json['id'], ''),
      safeToOperate: json['safe_to_operate'] == true,
      blockingReasons: reasons is List
          ? reasons.map((item) => item.toString()).toList(growable: false)
          : const [],
      predictionRisk: json['prediction_risk']?.toString(),
      predictionError: json['prediction_error']?.toString(),
      tripDistanceKm: json['trip_distance_km'] is num
          ? (json['trip_distance_km'] as num).toDouble()
          : null,
      batterySocUsed: json['battery_soc_used'] is num
          ? (json['battery_soc_used'] as num).toDouble()
          : null,
    );
  }
}

class DriverAlert {
  const DriverAlert({
    required this.id,
    required this.title,
    required this.message,
    required this.category,
    required this.severity,
    required this.timestamp,
    required this.acknowledged,
  });

  final String id;
  final String title;
  final String message;
  final String category;
  final AlertSeverity severity;
  final String timestamp;
  final bool acknowledged;

  DriverAlert copyWith({bool? acknowledged}) {
    return DriverAlert(
      id: id,
      title: title,
      message: message,
      category: category,
      severity: severity,
      timestamp: timestamp,
      acknowledged: acknowledged ?? this.acknowledged,
    );
  }

  factory DriverAlert.fromJson(Map<String, dynamic> json) {
    return DriverAlert(
      id: _stringValue(json['id'], ''),
      title: _stringValue(json['title'], 'Driver alert'),
      message: _stringValue(json['message'], ''),
      category: _stringValue(json['alert_type'], 'system'),
      severity: alertSeverityFromBackend(json['severity']),
      timestamp: _stringValue(
        json['created_at'] ?? json['resolved_at'],
        'Recent',
      ),
      acknowledged: _stringValue(json['status'], 'active') != 'active',
    );
  }
}

class TripEvent {
  const TripEvent({
    this.id = '',
    required this.time,
    required this.title,
    required this.description,
    required this.type,
  });

  final String id;
  final String time;
  final String title;
  final String description;
  final AlertSeverity type;

  factory TripEvent.fromJson(Map<String, dynamic> json) {
    return TripEvent(
      id: _stringValue(json['id'], ''),
      time: _stringValue(json['created_at'], 'Recent'),
      title: _stringValue(json['title'], 'Trip event'),
      description: _stringValue(
        json['description'],
        _stringValue(json['event_type'], 'Driver route event'),
      ),
      type: alertSeverityFromBackend(json['severity']),
    );
  }
}

class DriverLocationUpdate {
  const DriverLocationUpdate({
    required this.latitude,
    required this.longitude,
    this.accuracyM,
    this.heading,
    this.speedMps,
    this.recordedAt,
  });

  final double latitude;
  final double longitude;
  final double? accuracyM;
  final double? heading;
  final double? speedMps;
  final DateTime? recordedAt;

  Map<String, dynamic> toJson() {
    return {
      'latitude': latitude,
      'longitude': longitude,
      if (accuracyM != null) 'accuracy_m': accuracyM,
      if (heading != null) 'heading': heading,
      if (speedMps != null) 'speed_mps': speedMps,
      if (recordedAt != null) 'recorded_at': recordedAt!.toIso8601String(),
    };
  }
}

class DriverTripSession {
  const DriverTripSession({
    required this.id,
    required this.routeId,
    required this.status,
    this.routeCode,
    this.startedAt,
    this.endedAt,
  });

  final String id;
  final String routeId;
  final String status;
  final String? routeCode;
  final String? startedAt;
  final String? endedAt;

  factory DriverTripSession.fromJson(Map<String, dynamic> json) {
    return DriverTripSession(
      id: _stringValue(json['trip_session_id'], ''),
      routeId: _stringValue(json['route_id'], ''),
      routeCode: _stringValue(json['route_code'], ''),
      status: _stringValue(json['status'], 'active'),
      startedAt: json['started_at']?.toString(),
      endedAt: json['ended_at']?.toString(),
    );
  }
}

class TripReadiness {
  const TripReadiness({
    required this.canStart,
    required this.vehicleRegistration,
    required this.vehicleCategory,
    required this.vehicleStatus,
    required this.maintenanceRisk,
    required this.routeDelayRisk,
    required this.demandLevels,
    required this.routeDistanceKm,
    required this.warnings,
    required this.blockingReasons,
  });

  final bool canStart;
  final String vehicleRegistration;
  final String vehicleCategory;
  final String vehicleStatus;
  final String maintenanceRisk;
  final String routeDelayRisk;
  final List<String> demandLevels;
  final double routeDistanceKm;
  final List<String> warnings;
  final List<String> blockingReasons;

  factory TripReadiness.empty() => const TripReadiness(
    canStart: false,
    vehicleRegistration: 'No assigned vehicle',
    vehicleCategory: 'unknown',
    vehicleStatus: 'unassigned',
    maintenanceRisk: 'unknown',
    routeDelayRisk: 'unknown',
    demandLevels: [],
    routeDistanceKm: 0,
    warnings: [],
    blockingReasons: ['No dispatched route and vehicle are assigned'],
  );

  factory TripReadiness.fromJson(Map<String, dynamic> json) {
    List<String> values(Object? value) => value is List
        ? value.map((item) => item.toString()).toList(growable: false)
        : const [];
    return TripReadiness(
      canStart: json['can_start'] == true,
      vehicleRegistration: _stringValue(
        json['vehicle_registration'],
        'No assigned vehicle',
      ),
      vehicleCategory: _stringValue(json['vehicle_category'], 'unknown'),
      vehicleStatus: _stringValue(json['vehicle_status'], 'unknown'),
      maintenanceRisk: _stringValue(json['maintenance_risk'], 'unknown'),
      routeDelayRisk: _stringValue(json['route_delay_risk'], 'unknown'),
      demandLevels: values(json['demand_levels']),
      routeDistanceKm: _doubleValue(json['route_distance_km'], 0),
      warnings: values(json['warnings']),
      blockingReasons: values(json['blocking_reasons']),
    );
  }
}
