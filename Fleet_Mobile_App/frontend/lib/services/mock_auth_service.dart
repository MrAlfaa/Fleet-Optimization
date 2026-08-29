import '../models/driver_models.dart';
import 'driver_service_contracts.dart';

class MockAuthService implements DriverAuthService {
  bool enrolled = false;
  bool pinConfigured = false;
  @override
  String? get accessToken => 'mock-token';
  @override
  Future<bool> hasEnrollment() async => enrolled;
  @override
  Future<bool> requiresPinSetup() async => enrolled && !pinConfigured;
  @override
  Future<DriverUser> enroll({
    required String username,
    required String temporaryPassword,
  }) async {
    enrolled = true;
    return _user(username);
  }

  @override
  Future<void> configurePin(
    String pin, {
    required bool enableBiometrics,
  }) async {
    pinConfigured = true;
  }

  @override
  Future<DriverUser> unlockWithPin(String pin) async => _user('driver.demo');
  @override
  Future<DriverUser> unlockWithBiometrics() async => _user('driver.demo');
  @override
  Future<DriverUser> refreshSession() async => _user('driver.demo');
  @override
  Future<bool> canUseBiometrics() async => true;
  @override
  Future<void> logout() async {}
  @override
  Future<void> clearEnrollment() async {
    enrolled = false;
    pinConfigured = false;
  }

  DriverUser _user(String username) => DriverUser(
    id: 'drv-001',
    name: 'Driver Demo',
    email: '$username@fleet.local',
    role: 'driver',
  );
}
