import 'dart:convert';
import 'dart:math';

import 'package:cryptography/cryptography.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import 'package:uuid/uuid.dart';

import '../models/driver_models.dart';
import 'api_client.dart';
import 'driver_service_contracts.dart';

class AuthApiService implements DriverAuthService {
  AuthApiService({required ApiClient apiClient, FlutterSecureStorage? storage, LocalAuthentication? localAuth})
      : _apiClient = apiClient,
        _storage = storage ?? const FlutterSecureStorage(aOptions: AndroidOptions(encryptedSharedPreferences: true)),
        _localAuth = localAuth ?? LocalAuthentication();

  static const _installationKey = 'driver_installation_id';
  static const _secretKey = 'driver_device_secret';
  static const _pinHashKey = 'driver_pin_hash';
  static const _pinSaltKey = 'driver_pin_salt';
  static const _biometricKey = 'driver_biometric_enabled';
  static const _failedKey = 'driver_pin_failures';
  static const _lockedUntilKey = 'driver_pin_locked_until';

  final ApiClient _apiClient;
  final FlutterSecureStorage _storage;
  final LocalAuthentication _localAuth;
  String? _accessToken;

  @override
  String? get accessToken => _accessToken;
  @override
  Future<bool> hasEnrollment() async => (await _storage.read(key: _secretKey))?.isNotEmpty == true;
  @override
  Future<bool> requiresPinSetup() async => await hasEnrollment() && (await _storage.read(key: _pinHashKey)) == null;

  @override
  Future<DriverUser> enroll({required String username, required String temporaryPassword}) async {
    final android = await DeviceInfoPlugin().androidInfo;
    final data = await _apiClient.post<Map<String, dynamic>>('/driver-device/enroll', {
      'username': username.trim().toLowerCase(), 'temporary_password': temporaryPassword,
      'installation_id': await _installationId(), 'device_name': '${android.manufacturer} ${android.model}',
      'device_model': android.model, 'android_version': android.version.release, 'app_version': '1.0.0',
    });
    final user = _parseSession(data);
    await _storage.write(key: _secretKey, value: data['device_secret']?.toString());
    return user;
  }

  @override
  Future<void> configurePin(String pin, {required bool enableBiometrics}) async {
    if (!RegExp(r'^\d{6}$').hasMatch(pin)) throw const AuthException('PIN must contain exactly six digits.');
    final salt = List<int>.generate(16, (_) => Random.secure().nextInt(256));
    final hash = await _derivePin(pin, salt);
    await _storage.write(key: _pinSaltKey, value: base64Encode(salt));
    await _storage.write(key: _pinHashKey, value: base64Encode(hash));
    await _storage.write(key: _biometricKey, value: enableBiometrics.toString());
    if (_accessToken == null) await _createSession();
    await _apiClient.patch<Map<String, dynamic>>('/driver-device/biometric', {'biometric_enabled': enableBiometrics});
  }

  @override
  Future<DriverUser> unlockWithPin(String pin) async {
    final lockedUntil = DateTime.tryParse(await _storage.read(key: _lockedUntilKey) ?? '');
    if (lockedUntil != null && lockedUntil.isAfter(DateTime.now().toUtc())) throw AuthException('PIN entry is locked until ${lockedUntil.toLocal()}.');
    final salt = base64Decode(await _required(_pinSaltKey));
    if (base64Encode(await _derivePin(pin, salt)) != await _required(_pinHashKey)) {
      final failures = (int.tryParse(await _storage.read(key: _failedKey) ?? '0') ?? 0) + 1;
      await _storage.write(key: _failedKey, value: failures.toString());
      if (failures >= 5) {
        await _storage.write(key: _lockedUntilKey, value: DateTime.now().toUtc().add(const Duration(minutes: 15)).toIso8601String());
        await _storage.write(key: _failedKey, value: '0');
      }
      throw const AuthException('Incorrect PIN.');
    }
    await _storage.delete(key: _failedKey); await _storage.delete(key: _lockedUntilKey);
    return _createSession();
  }

  @override
  Future<DriverUser> unlockWithBiometrics() async {
    if (await _storage.read(key: _biometricKey) != 'true') throw const AuthException('Biometric unlock is not enabled.');
    final accepted = await _localAuth.authenticate(localizedReason: 'Unlock FleetOpt Driver', options: const AuthenticationOptions(biometricOnly: true, stickyAuth: true));
    if (!accepted) throw const AuthException('Biometric authentication was cancelled or failed.');
    return _createSession();
  }

  @override
  Future<bool> canUseBiometrics() async => await _localAuth.isDeviceSupported() && await _localAuth.canCheckBiometrics;

  Future<DriverUser> _createSession() async {
    try {
      final data = await _apiClient.post<Map<String, dynamic>>('/driver-device/session', {'installation_id': await _installationId(), 'device_secret': await _required(_secretKey)});
      return _parseSession(data);
    } on ApiException catch (error) {
      if (error.statusCode == 401 || error.statusCode == 403) await clearEnrollment();
      throw AuthException(error.message);
    }
  }

  DriverUser _parseSession(Map<String, dynamic> data) {
    final token = data['access_token']?.toString(); final rawUser = data['user'];
    if (token == null || rawUser is! Map<String, dynamic>) throw const AuthException('Backend returned an invalid device session.');
    final user = DriverUser.fromJson(rawUser);
    if (user.role != 'driver') throw const AuthException('Only driver accounts can use this application.');
    _accessToken = token; return user;
  }

  Future<List<int>> _derivePin(String pin, List<int> salt) async {
    final algorithm = Pbkdf2(macAlgorithm: Hmac.sha256(), iterations: 120000, bits: 256);
    final key = await algorithm.deriveKey(secretKey: SecretKey(utf8.encode(pin)), nonce: salt);
    return key.extractBytes();
  }

  Future<String> _installationId() async {
    final current = await _storage.read(key: _installationKey); if (current != null) return current;
    final value = const Uuid().v4(); await _storage.write(key: _installationKey, value: value); return value;
  }

  Future<String> _required(String key) async {
    final value = await _storage.read(key: key);
    if (value == null || value.isEmpty) throw const AuthException('Device registration is incomplete. Ask the fleet administrator to reset it.');
    return value;
  }

  @override
  Future<void> logout() async { _accessToken = null; }
  @override
  Future<void> clearEnrollment() async { _accessToken = null; await _storage.deleteAll(); }
}
