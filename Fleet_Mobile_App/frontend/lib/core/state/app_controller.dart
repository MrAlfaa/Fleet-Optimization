import 'package:flutter/material.dart';

import '../../models/driver_models.dart';
import '../../services/mock_auth_service.dart';
import '../../services/mock_driver_service.dart';

class AppController extends ChangeNotifier {
  AppController({required this.authService, required this.driverService});

  final MockAuthService authService;
  final MockDriverService driverService;

  DriverUser? user;
  late AssignedVehicle vehicle;
  late DriverRoute route;
  late List<DriverAlert> alerts;
  late List<TripEvent> tripEvents;
  int selectedIndex = 0;
  bool tripActive = false;
  bool loading = false;
  String? error;

  bool get isAuthenticated => user != null;
  int get activeAlertCount =>
      alerts.where((alert) => !alert.acknowledged).length;

  Future<void> restoreSession() async {
    _loadDriverData();
    user = await authService.restoreSession();
  }

  Future<void> login(String email, String password) async {
    await _runAuth(() async {
      user = await authService.login(email: email, password: password);
    });
  }

  Future<void> register({
    required String name,
    required String email,
    required String inviteCode,
    required String password,
  }) async {
    await _runAuth(() async {
      user = await authService.register(
        name: name,
        email: email,
        inviteCode: inviteCode,
        password: password,
      );
    });
  }

  Future<void> logout() async {
    await authService.logout();
    user = null;
    selectedIndex = 0;
    notifyListeners();
  }

  void selectTab(int index) {
    selectedIndex = index;
    notifyListeners();
  }

  void toggleTrip() {
    tripActive = !tripActive;
    tripEvents = [
      TripEvent(
        time: tripActive ? 'Now' : 'Ended',
        title: tripActive ? 'Trip started' : 'Trip completed',
        description: tripActive
            ? 'Mock trip is active. Real GPS sync is a later backend phase.'
            : 'Trip state stored locally for this frontend prototype.',
        type: AlertSeverity.info,
      ),
      ...tripEvents,
    ];
    notifyListeners();
  }

  void updateStopStatus(String stopId, DeliveryStatus status) {
    final stops = route.stops
        .map((stop) => stop.id == stopId ? stop.copyWith(status: status) : stop)
        .toList(growable: false);
    route = route.copyWith(stops: stops);
    notifyListeners();
  }

  void acknowledgeAlert(String alertId) {
    alerts = alerts
        .map(
          (alert) =>
              alert.id == alertId ? alert.copyWith(acknowledged: true) : alert,
        )
        .toList(growable: false);
    notifyListeners();
  }

  void clearError() {
    error = null;
    notifyListeners();
  }

  void _loadDriverData() {
    vehicle = driverService.getAssignedVehicle();
    route = driverService.getTodayRoute();
    alerts = driverService.getAlerts();
    tripEvents = driverService.getTripEvents();
  }

  Future<void> _runAuth(Future<void> Function() action) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      await action();
    } on AuthException catch (exception) {
      error = exception.message;
    } catch (_) {
      error = 'Unable to complete authentication. Try again.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }
}
