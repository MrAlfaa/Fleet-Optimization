import '../models/driver_models.dart';

class AuthException implements Exception {
  const AuthException(this.message);

  final String message;

  @override
  String toString() => message;
}

abstract class DriverAuthService {
  String? get accessToken;

  Future<bool> hasEnrollment();
  Future<bool> requiresPinSetup();
  Future<DriverUser> enroll({
    required String username,
    required String temporaryPassword,
  });
  Future<void> configurePin(String pin, {required bool enableBiometrics});
  Future<DriverUser> unlockWithPin(String pin);
  Future<DriverUser> unlockWithBiometrics();
  Future<bool> canUseBiometrics();
  Future<void> logout();
  Future<void> clearEnrollment();
}

abstract class DriverDataService {
  Future<AssignedVehicle?> getAssignedVehicle();
  Future<DriverRoute?> getTodayRoute();
  Future<List<DriverAlert>> getAlerts();
  Future<List<TripEvent>> getTripEvents();
  Future<TripReadiness> getTripReadiness();
  Future<DriverInspectionResult> submitPreTripInspection(
    PreTripInspection inspection,
  );
  Future<DriverInspectionResult> submitPostTripInspection(
    PostTripInspection inspection,
  );
  Future<DriverTripSession> startTrip();
  Future<DriverTripSession> endTrip();
  Future<void> sendLocation(DriverLocationUpdate location);
  Future<void> updateDeliveryStatus(String orderId, DeliveryStatus status);
  Future<void> markDeliveryIncomplete(
    String orderId, {
    required String reason,
    String? details,
  });
  Future<void> acknowledgeAlert(String alertId);
  Future<void> submitIssue({
    required String title,
    required String message,
    String severity = 'warning',
    String? vehicleId,
    String? routeId,
    String category,
  });
}
