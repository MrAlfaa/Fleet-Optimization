import 'package:shared_preferences/shared_preferences.dart';

import '../models/driver_models.dart';

class MockAuthService {
  static const _sessionKey = 'fleetopt.driver.session.v1';

  Future<DriverUser?> restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    final email = prefs.getString(_sessionKey);
    if (email == null) return null;
    return DriverUser(
      id: 'drv-001',
      name: email.contains('sarah') ? 'Sarah Jenkins' : 'Marcus Johnson',
      email: email,
      role: 'driver',
    );
  }

  Future<DriverUser> login({
    required String email,
    required String password,
  }) async {
    if (!email.contains('@') || password.length < 6) {
      throw AuthException(
        'Use a valid email and at least 6 password characters.',
      );
    }
    return _persist(email);
  }

  Future<DriverUser> register({
    required String name,
    required String email,
    required String inviteCode,
    required String password,
  }) async {
    if (name.trim().length < 2) {
      throw AuthException('Enter the driver name.');
    }
    if (inviteCode.trim().length < 4) {
      throw AuthException('Enter a valid fleet invite code.');
    }
    if (!email.contains('@') || password.length < 6) {
      throw AuthException(
        'Use a valid email and at least 6 password characters.',
      );
    }
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionKey, email);
    return DriverUser(
      id: 'drv-001',
      name: name.trim(),
      email: email,
      role: 'driver',
    );
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_sessionKey);
  }

  Future<DriverUser> _persist(String email) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_sessionKey, email);
    return DriverUser(
      id: 'drv-001',
      name: 'Marcus Johnson',
      email: email,
      role: 'driver',
    );
  }
}

class AuthException implements Exception {
  const AuthException(this.message);
  final String message;
}
