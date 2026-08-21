import 'package:flutter_test/flutter_test.dart';
import 'package:fleetopt_driver/models/driver_models.dart';

void main() {
  test('parses blocked trip readiness with actionable reasons', () {
    final readiness = TripReadiness.fromJson({
      'can_start': false,
      'vehicle_registration': 'WP CAA-1234',
      'vehicle_category': 'electric_van',
      'vehicle_status': 'blocked',
      'maintenance_risk': 'critical',
      'route_delay_risk': 'medium',
      'demand_levels': ['high'],
      'route_distance_km': 48.2,
      'warnings': ['High parcel demand is expected on this route'],
      'blocking_reasons': ['Latest predictive maintenance risk is critical'],
    });

    expect(readiness.canStart, isFalse);
    expect(readiness.vehicleRegistration, 'WP CAA-1234');
    expect(
      readiness.blockingReasons,
      contains('Latest predictive maintenance risk is critical'),
    );
    expect(readiness.demandLevels, ['high']);
  });

  test('parses warning readiness without blocking trip start', () {
    final readiness = TripReadiness.fromJson({
      'can_start': true,
      'vehicle_status': 'warning',
      'maintenance_risk': 'high',
      'warnings': ['Vehicle health status requires monitoring'],
    });

    expect(readiness.canStart, isTrue);
    expect(readiness.warnings, isNotEmpty);
  });

  test('pre-trip inspection serializes only controlled backend values', () {
    const inspection = PreTripInspection(
      odometer: 42000,
      batterySoc: 72,
      tireCondition: 'worn',
      brakeCondition: 'normal',
      chargingCondition: 'normal',
      vehicleDamage: 'none',
      dashboardWarning: 'amber',
      unusualNoise: 'none',
      unusualVibration: 'mild',
    );

    expect(inspection.toJson(), containsPair('tire_condition', 'worn'));
    expect(inspection.toJson(), containsPair('battery_soc', 72.0));
    expect(inspection.toJson().containsKey('Battery_Voltage'), isFalse);
  });

  test('route next stop skips terminal deliveries in optimized order', () {
    final route = DriverRoute.fromAssignedRouteJson({
      'route': {'id': 'route-1', 'route_name': 'Route 1'},
      'stops': [
        {'id': 'one', 'sequence': 1, 'delivery_status': 'delivered'},
        {'id': 'two', 'sequence': 2, 'delivery_status': 'failed'},
        {'id': 'three', 'sequence': 3, 'delivery_status': 'assigned'},
      ],
    });

    expect(route.nextStop?.id, 'three');
  });
}
