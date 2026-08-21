import 'package:geolocator/geolocator.dart';

import '../models/driver_models.dart';

class DriverLocationService {
  Future<DriverLocationUpdate?> getCurrentLocation() async {
    final enabled = await Geolocator.isLocationServiceEnabled();
    if (!enabled) {
      return null;
    }

    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.denied ||
        permission == LocationPermission.deniedForever) {
      return null;
    }

    final position = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(accuracy: LocationAccuracy.high),
    );
    return DriverLocationUpdate(
      latitude: position.latitude,
      longitude: position.longitude,
      accuracyM: position.accuracy,
      heading: position.heading.isNaN ? null : position.heading,
      speedMps: position.speed.isNaN ? null : position.speed,
      recordedAt: position.timestamp,
    );
  }
}
