import 'package:fleetopt_driver/core/state/app_controller.dart';
import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:fleetopt_driver/services/mock_auth_service.dart';
import 'package:fleetopt_driver/services/mock_driver_service.dart';
import 'package:flutter_test/flutter_test.dart';

class _ReviewHeldService extends MockDriverService {
  int startCalls = 0;

  @override
  Future<TripReadiness> getTripReadiness() async {
    return const TripReadiness(
      canStart: false,
      vehicleRegistration: 'WP LO-2411',
      vehicleCategory: 'truck',
      vehicleStatus: 'blocked',
      maintenanceRisk: 'critical',
      routeDelayRisk: 'low',
      demandLevels: [],
      routeDistanceKm: 22,
      warnings: [],
      blockingReasons: ['Engineering review is required'],
      reviewStatus: 'pending',
    );
  }

  @override
  Future<DriverTripSession> startTrip() async {
    startCalls += 1;
    return super.startTrip();
  }
}

void main() {
  test('pending engineering review prevents backend trip start', () async {
    final service = _ReviewHeldService();
    final controller = AppController(
      authService: MockAuthService(),
      driverService: service,
    );
    await controller.refreshDriverData();

    await controller.startTripWithInspection(
      const PreTripInspection(
        odometer: 142500,
        tireCondition: 'normal',
        brakeCondition: 'normal',
        powertrainCondition: 'normal',
        chargingOrFuelIssue: 'none',
        vehicleDamage: 'none',
        dashboardWarning: 'none',
        unusualNoise: 'none',
        vibrationLevel: 'none',
      ),
    );

    expect(service.startCalls, 0);
    expect(controller.tripActive, isFalse);
    expect(controller.readiness.hasPendingEngineeringReview, isTrue);
    expect(controller.error, contains('Engineering review is required'));
  });
}
