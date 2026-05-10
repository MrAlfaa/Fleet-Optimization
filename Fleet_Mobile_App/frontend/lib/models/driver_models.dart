enum DeliveryStatus { pending, arrived, delivered, failed }

enum AlertSeverity { info, warning, critical }

class DriverUser {
  const DriverUser({
    required this.id,
    required this.name,
    required this.email,
    required this.role,
  });

  final String id;
  final String name;
  final String email;
  final String role;
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
}

class DriverRoute {
  const DriverRoute({
    required this.id,
    required this.title,
    required this.depot,
    required this.totalDistanceKm,
    required this.eta,
    required this.stops,
  });

  final String id;
  final String title;
  final String depot;
  final double totalDistanceKm;
  final String eta;
  final List<RouteStop> stops;

  int get completedStops =>
      stops.where((stop) => stop.status == DeliveryStatus.delivered).length;

  DriverRoute copyWith({List<RouteStop>? stops}) {
    return DriverRoute(
      id: id,
      title: title,
      depot: depot,
      totalDistanceKm: totalDistanceKm,
      eta: eta,
      stops: stops ?? this.stops,
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
}

class TripEvent {
  const TripEvent({
    required this.time,
    required this.title,
    required this.description,
    required this.type,
  });

  final String time;
  final String title;
  final String description;
  final AlertSeverity type;
}
