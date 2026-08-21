import 'dart:async';

import 'package:flutter/material.dart';

import '../../models/driver_models.dart';
import '../../services/driver_service_contracts.dart';
import '../../services/location_service.dart';

class AppController extends ChangeNotifier {
  AppController({
    required this.authService,
    required this.driverService,
    DriverLocationService? locationService,
  }) : locationService = locationService ?? DriverLocationService();

  final DriverAuthService authService;
  final DriverDataService driverService;
  final DriverLocationService locationService;

  DriverUser? user;
  DriverTripSession? tripSession;
  DriverInspectionResult? latestInspection;
  TripReadiness readiness = TripReadiness.empty();
  AssignedVehicle vehicle = AssignedVehicle.empty();
  DriverRoute route = DriverRoute.empty();
  List<DriverAlert> alerts = [];
  List<TripEvent> tripEvents = [];
  int selectedIndex = 0;
  bool tripActive = false;
  bool locationSharingUnavailable = false;
  bool loading = false;
  bool enrolled = false;
  bool pinSetupRequired = false;
  String? error;
  Timer? _locationTimer;

  bool get isAuthenticated => user != null && !pinSetupRequired;
  int get activeAlertCount =>
      alerts.where((alert) => !alert.acknowledged).length;

  Future<void> restoreSession() async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      enrolled = await authService.hasEnrollment();
      pinSetupRequired = enrolled && await authService.requiresPinSetup();
    } catch (_) {
      error = 'Unable to restore driver session. Please sign in again.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> enroll(String username, String temporaryPassword) async {
    await _runAuth(() async {
      user = await authService.enroll(
        username: username,
        temporaryPassword: temporaryPassword,
      );
      enrolled = true;
      pinSetupRequired = true;
    });
  }

  Future<void> configurePin(
    String pin, {
    required bool enableBiometrics,
  }) async {
    await _runAuth(() async {
      await authService.configurePin(pin, enableBiometrics: enableBiometrics);
      pinSetupRequired = false;
    });
  }

  Future<void> unlockWithPin(String pin) async => _runAuth(() async {
    user = await authService.unlockWithPin(pin);
  });
  Future<void> unlockWithBiometrics() async => _runAuth(() async {
    user = await authService.unlockWithBiometrics();
  });
  Future<bool> canUseBiometrics() => authService.canUseBiometrics();

  Future<void> logout() async {
    await authService.logout();
    user = null;
    vehicle = AssignedVehicle.empty();
    route = DriverRoute.empty();
    alerts = [];
    tripEvents = [];
    tripActive = false;
    tripSession = null;
    readiness = TripReadiness.empty();
    locationSharingUnavailable = false;
    _stopLocationTimer();
    selectedIndex = 0;
    notifyListeners();
  }

  Future<void> forgetDevice() async {
    await authService.clearEnrollment();
    enrolled = false;
    pinSetupRequired = false;
    user = null;
    notifyListeners();
  }

  Future<void> handleDeviceRevoked() => forgetDevice();

  void lockApp() {
    if (!enrolled) return;
    authService.logout();
    user = null;
    _stopLocationTimer();
    notifyListeners();
  }

  void selectTab(int index) {
    selectedIndex = index;
    notifyListeners();
  }

  Future<void> startTripWithInspection(PreTripInspection inspection) async =>
      _startTrip(inspection);

  Future<void> endTripWithInspection(PostTripInspection inspection) async =>
      _endTrip(inspection);

  Future<void> updateStopStatus(String stopId, DeliveryStatus status) async {
    error = null;
    try {
      await driverService.updateDeliveryStatus(stopId, status);
      final stops = route.stops
          .map(
            (stop) => stop.id == stopId ? stop.copyWith(status: status) : stop,
          )
          .toList(growable: false);
      route = route.copyWith(stops: stops);
      await refreshDriverData(notifyLoading: false);
    } catch (_) {
      error = 'Unable to update delivery status. Check backend connection.';
    } finally {
      notifyListeners();
    }
  }

  Future<void> markDeliveryIncomplete(
    String stopId, {
    required String reason,
    String? details,
  }) async {
    error = null;
    try {
      await driverService.markDeliveryIncomplete(
        stopId,
        reason: reason,
        details: details,
      );
      await refreshDriverData(notifyLoading: false);
    } catch (exception) {
      error = exception.toString();
      rethrow;
    } finally {
      notifyListeners();
    }
  }

  Future<void> acknowledgeAlert(String alertId) async {
    error = null;
    try {
      await driverService.acknowledgeAlert(alertId);
      alerts = alerts
          .map(
            (alert) => alert.id == alertId
                ? alert.copyWith(acknowledged: true)
                : alert,
          )
          .toList(growable: false);
    } catch (_) {
      error = 'Unable to acknowledge alert. Check backend connection.';
    } finally {
      notifyListeners();
    }
  }

  Future<void> submitIssue({
    required String title,
    required String message,
    String severity = 'warning',
    String category = 'other',
  }) async {
    error = null;
    try {
      await driverService.submitIssue(
        title: title,
        message: message,
        severity: severity,
        category: category,
        vehicleId: vehicle.id.isEmpty ? null : vehicle.id,
        routeId: route.id.isEmpty ? null : route.id,
      );
      await refreshDriverData(notifyLoading: false);
    } catch (_) {
      error = 'Unable to submit issue report. Check backend connection.';
      notifyListeners();
      rethrow;
    }
  }

  void clearError() {
    error = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _stopLocationTimer();
    super.dispose();
  }

  Future<void> refreshDriverData({bool notifyLoading = true}) async {
    if (notifyLoading) {
      loading = true;
      notifyListeners();
    }
    error = null;
    try {
      vehicle =
          await driverService.getAssignedVehicle() ?? AssignedVehicle.empty();
      route = await driverService.getTodayRoute() ?? DriverRoute.empty();
      alerts = await driverService.getAlerts();
      tripEvents = await driverService.getTripEvents();
      readiness = await driverService.getTripReadiness();
    } catch (_) {
      vehicle = AssignedVehicle.empty();
      route = DriverRoute.empty();
      alerts = [];
      tripEvents = const [
        TripEvent(
          time: 'Offline',
          title: 'Backend unavailable',
          description:
              'Unable to load assigned route data. Confirm backend API is running.',
          type: AlertSeverity.warning,
        ),
      ];
      readiness = TripReadiness.empty();
      error = 'Unable to load assigned route data.';
    } finally {
      if (notifyLoading) {
        loading = false;
      }
      notifyListeners();
    }
  }

  Future<void> _runAuth(Future<void> Function() action) async {
    loading = true;
    error = null;
    notifyListeners();
    try {
      await action();
      if (user != null) {
        await refreshDriverData(notifyLoading: false);
      }
    } on AuthException catch (exception) {
      error = exception.message;
    } catch (_) {
      error = 'Unable to complete authentication. Try again.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> _startTrip(PreTripInspection inspection) async {
    if (!route.hasAssignedRoute) {
      error = 'No dispatched route is assigned to this driver.';
      notifyListeners();
      return;
    }

    loading = true;
    error = null;
    notifyListeners();
    try {
      latestInspection = await driverService.submitPreTripInspection(
        inspection,
      );
      if (!latestInspection!.safeToOperate) {
        error =
            '${latestInspection!.blockingReasons.join('. ')}. Contact the fleet manager.';
        return;
      }
      readiness = await driverService.getTripReadiness();
      if (!readiness.canStart) {
        error = readiness.blockingReasons.isNotEmpty
            ? '${readiness.blockingReasons.join('. ')}. Contact the fleet manager.'
            : 'This vehicle is not safe to dispatch. Contact the fleet manager.';
        return;
      }
      tripSession = await driverService.startTrip();
      tripActive = true;
      tripEvents = [
        const TripEvent(
          time: 'Now',
          title: 'Trip started',
          description: 'Backend live trip session is active.',
          type: AlertSeverity.info,
        ),
        ...tripEvents,
      ];
      await _sendLocationUpdate(showPermissionWarning: true);
      _startLocationTimer();
      await refreshDriverData(notifyLoading: false);
    } catch (exception) {
      tripActive = false;
      tripSession = null;
      _stopLocationTimer();
      error = exception.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> _endTrip(PostTripInspection inspection) async {
    loading = true;
    error = null;
    notifyListeners();
    _stopLocationTimer();
    try {
      latestInspection = await driverService.submitPostTripInspection(
        inspection,
      );
      tripSession = await driverService.endTrip();
      tripActive = false;
      tripEvents = [
        const TripEvent(
          time: 'Ended',
          title: 'Trip completed',
          description: 'Backend trip session was closed.',
          type: AlertSeverity.info,
        ),
        ...tripEvents,
      ];
      await refreshDriverData(notifyLoading: false);
    } catch (_) {
      error = 'Unable to end trip. Check backend connection.';
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  void _startLocationTimer() {
    _stopLocationTimer();
    _locationTimer = Timer.periodic(const Duration(seconds: 20), (_) {
      _sendLocationUpdate();
    });
  }

  void _stopLocationTimer() {
    _locationTimer?.cancel();
    _locationTimer = null;
  }

  Future<void> _sendLocationUpdate({bool showPermissionWarning = false}) async {
    final location = await locationService.getCurrentLocation();
    if (location == null) {
      locationSharingUnavailable = true;
      if (showPermissionWarning) {
        tripEvents = [
          const TripEvent(
            time: 'GPS',
            title: 'Location sharing unavailable',
            description:
                'Trip started, but GPS permission or device location is unavailable.',
            type: AlertSeverity.warning,
          ),
          ...tripEvents,
        ];
      }
      return;
    }

    try {
      await driverService.sendLocation(location);
      locationSharingUnavailable = false;
    } catch (_) {
      _stopLocationTimer();
      error = 'Unable to send live location. Location sync stopped.';
      notifyListeners();
    }
  }
}
