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

  static Uri routeUri(DriverRoute route) {
    final stops = route.stops
        .where((stop) => stop.latitude != 0 && stop.longitude != 0)
        .toList(growable: false);
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
    return launchUrl(stopUri(stop), mode: LaunchMode.externalApplication);
  }

  static Future<bool> openRoute(DriverRoute route) {
    if (!route.hasAssignedRoute) {
      return Future.value(false);
    }
    return launchUrl(routeUri(route), mode: LaunchMode.externalApplication);
  }
}
