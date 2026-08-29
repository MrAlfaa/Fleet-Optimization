import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:fleetopt_driver/services/map_navigation_service.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const stop = RouteStop(
    id: 'stop-1',
    sequence: 1,
    customer: 'Customer',
    address: 'Nugegoda',
    zone: 'Nugegoda',
    eta: '10:00',
    priority: 'high',
    latitude: 6.8649,
    longitude: 79.8997,
    status: DeliveryStatus.pending,
  );

  test('builds a key-free geo fallback for a stop', () {
    final uri = GoogleMapsNavigation.stopFallbackUri(stop);

    expect(uri.scheme, 'geo');
    expect(uri.toString(), contains('6.8649,79.8997'));
    expect(uri.toString(), contains('Nugegoda'));
  });

  test('full route navigation follows optimized sequence order', () {
    final route = DriverRoute(
      id: 'route-1',
      title: 'Route',
      depot: 'Depot',
      depotLatitude: 6.9271,
      depotLongitude: 79.8612,
      totalDistanceKm: 10,
      eta: '30 min',
      stops: [
        const RouteStop(
          id: 'stop-2',
          sequence: 2,
          customer: 'Second',
          address: 'Malabe',
          zone: 'Malabe',
          eta: '10:30',
          priority: 'medium',
          latitude: 6.9061,
          longitude: 79.9696,
          status: DeliveryStatus.pending,
        ),
        stop,
      ],
    );

    final uri = GoogleMapsNavigation.routeUri(route);

    expect(uri.queryParameters['destination'], '6.9061,79.9696');
    expect(uri.queryParameters['waypoints'], '6.8649,79.8997');
  });
}
