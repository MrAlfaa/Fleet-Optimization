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
      tireCondition: 'warning',
      brakeCondition: 'normal',
      powertrainCondition: 'warning',
      chargingOrFuelIssue: 'none',
      vehicleDamage: 'none',
      dashboardWarning: 'amber',
      unusualNoise: 'none',
      vibrationLevel: 'mild',
    );

    expect(inspection.toJson(), containsPair('tire_condition', 'warning'));
    expect(inspection.toJson(), containsPair('battery_soc', 72.0));
    expect(
      inspection.toJson(),
      containsPair('powertrain_condition', 'warning'),
    );
    expect(inspection.toJson(), containsPair('charging_or_fuel_issue', 'none'));
    expect(inspection.toJson(), containsPair('vibration_level', 'mild'));
    expect(inspection.toJson().containsKey('charging_condition'), isFalse);
    expect(inspection.toJson().containsKey('Battery_Voltage'), isFalse);
  });

  test('non-electric inspection omits battery context when unavailable', () {
    const inspection = PostTripInspection(
      endingOdometer: 42120,
      tireCondition: 'normal',
      brakeCondition: 'warning',
      powertrainCondition: 'normal',
      chargingOrFuelIssue: 'warning',
      vehicleDamage: 'none',
      dashboardWarning: 'none',
      unusualNoise: 'mild',
      vibrationLevel: 'none',
    );

    expect(inspection.toJson().containsKey('ending_battery_soc'), isFalse);
    expect(inspection.toJson(), containsPair('brake_condition', 'warning'));
    expect(
      inspection.toJson(),
      containsPair('charging_or_fuel_issue', 'warning'),
    );
    expect(inspection.toJson().containsKey('trip_distance_km'), isFalse);
  });

  test('assigned vehicle exposes canonical powertrain and category', () {
    final diesel = AssignedVehicle.fromJson({
      'id': 'vehicle-1',
      'registration_number': 'WP LO-2411',
      'vehicle_category': 'truck',
      'vehicle_type': 'diesel_truck',
      'fuel_type': 'diesel',
      'current_mileage': 83000,
    });

    expect(diesel.category, 'truck');
    expect(diesel.fuelType, 'diesel');
    expect(diesel.supportsBatteryContext, isFalse);
    expect(diesel.energyIssueLabel, 'Fuel system condition');

    final hybrid = AssignedVehicle.fromJson({
      'vehicle_category': 'van',
      'fuel_type': 'hybrid',
    });
    expect(hybrid.supportsBatteryContext, isTrue);
    expect(hybrid.energyIssueLabel, 'Charging or fuel system condition');
  });

  test('parses pending engineering review as an actionable trip hold', () {
    final readiness = TripReadiness.fromJson({
      'can_start': false,
      'review_status': 'pending',
      'blocking_reasons': [
        'Engineering review is required before this vehicle can start',
      ],
    });

    expect(readiness.reviewStatus, 'pending');
    expect(readiness.hasPendingEngineeringReview, isTrue);
    expect(readiness.canStart, isFalse);
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

  test(
    'assigned route keeps next-stop parcel identity and handling details',
    () {
      final route = DriverRoute.fromAssignedRouteJson({
        'route': {'id': 'route-1', 'route_name': 'Route 1'},
        'stops': [
          {
            'id': 'parcel-db-id',
            'sequence': 1,
            'parcel_code': 'ORD-20260829-001',
            'customer_name': 'Colombo Customer',
            'customer_phone': '0771234567',
            'drop_address': 'Union Place, Colombo',
            'drop_latitude': 6.9147,
            'drop_longitude': 79.8729,
            'parcel_weight_kg': 12.5,
            'dimensions_cm': {'length': 60, 'width': 40, 'height': 35},
            'handling': ['Fragile', 'Do not tilt'],
            'delivery_status': 'in_route',
          },
        ],
      });

      expect(route.nextStop?.parcelCode, 'ORD-20260829-001');
      expect(route.nextStop?.customerPhone, '0771234567');
      expect(route.nextStop?.parcelWeightKg, 12.5);
      expect(route.nextStop?.dimensionsLabel, '60 x 40 x 35 cm');
      expect(route.nextStop?.handling, ['Fragile', 'Do not tilt']);
    },
  );

  test('assigned route keeps consolidation and load ownership', () {
    final route = DriverRoute.fromAssignedRouteJson({
      'route': {
        'id': 'route-1',
        'route_name': 'Consolidated load route',
        'consolidation_id': 'PCID202608292H001',
        'route_set_id': 'RSET-20260829-001',
        'load_plan_id': 'LOADPLAN-20260829-001',
        'load_id': 'LOAD-001',
        'assigned_stop_count': 2,
      },
      'stops': [
        {'id': 'one', 'sequence': 1},
        {'id': 'two', 'sequence': 2},
      ],
    });

    expect(route.consolidationId, 'PCID202608292H001');
    expect(route.routeSetId, 'RSET-20260829-001');
    expect(route.loadPlanId, 'LOADPLAN-20260829-001');
    expect(route.loadId, 'LOAD-001');
    expect(route.assignedStopCount, 2);
    expect(route.stops, hasLength(2));
  });
}
