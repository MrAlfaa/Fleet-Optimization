import 'package:url_launcher/url_launcher.dart';

import '../models/driver_models.dart';

class GoogleMapsNavigation {
  const GoogleMapsNavigation._();

  static Uri stopUri(RouteStop stop) {
    return Uri.https('www.google.com', '/maps/dir/', {
      'api': '1',
      'destination': '${stop.latitude},${stop.longitude}',
      'travelmode': 'driving',
    });
  }

  static Uri stopFallbackUri(RouteStop stop) {
    final coordinates = '${stop.latitude},${stop.longitude}';
    return Uri(
      scheme: 'geo',
      path: coordinates,
      queryParameters: {'q': '$coordinates(${stop.address})'},
    );
  }

  static Uri routeUri(DriverRoute route) {
    final stops =
        route.stops
            .where((stop) => stop.latitude != 0 && stop.longitude != 0)
            .toList(growable: false)
          ..sort((left, right) => left.sequence.compareTo(right.sequence));
    final destination = stops.isNotEmpty ? stops.last : null;
    final waypoints = stops.length > 1
        ? stops
              .take(stops.length - 1)
              .map((stop) => '${stop.latitude},${stop.longitude}')
              .join('|')
        : null;

    final params = <String, String>{
      'api': '1',
      'travelmode': 'driving',
      if (route.depotLatitude != 0 && route.depotLongitude != 0)
        'origin': '${route.depotLatitude},${route.depotLongitude}',
      if (destination != null)
        'destination': '${destination.latitude},${destination.longitude}',
      if (waypoints != null && waypoints.isNotEmpty) 'waypoints': waypoints,
    };
    return Uri.https('www.google.com', '/maps/dir/', params);
  }

  static Future<bool> openStop(RouteStop stop) {
    return _launchWithFallback(stopUri(stop), stopFallbackUri(stop));
  }

  static Future<bool> openRoute(DriverRoute route) {
    if (!route.hasAssignedRoute) {
      return Future.value(false);
    }
    final orderedStops = [...route.stops]
      ..sort((left, right) => left.sequence.compareTo(right.sequence));
    final destination = orderedStops.isEmpty ? null : orderedStops.last;
    if (destination == null) return Future.value(false);
    return _launchWithFallback(routeUri(route), stopFallbackUri(destination));
  }

  static Future<bool> _launchWithFallback(Uri primary, Uri fallback) async {
    final opened = await launchUrl(
      primary,
      mode: LaunchMode.externalApplication,
    );
    if (opened) return true;
    return launchUrl(fallback, mode: LaunchMode.externalApplication);
  }
}
