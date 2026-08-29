import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const route = DriverRoute(
    id: 'route-1',
    title: 'Colombo East',
    depot: 'Colombo depot',
    depotLatitude: 6.9271,
    depotLongitude: 79.8612,
    totalDistanceKm: 12.4,
    eta: '42 min',
    stops: [
      RouteStop(
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
      RouteStop(
        id: 'stop-1',
        sequence: 1,
        customer: 'First',
        address: 'Nugegoda',
        zone: 'Nugegoda',
        eta: '10:00',
        priority: 'high',
        latitude: 6.8649,
        longitude: 79.8997,
        status: DeliveryStatus.pending,
      ),
    ],
  );

  test('parses authoritative backend route coordinate objects', () {
    final geometry = RouteGeometry.fromJson({
      'route_id': 'route-1',
      'geometry_source': 'osrm',
      'cached': true,
      'coordinates': [
        {'latitude': 6.9271, 'longitude': 79.8612},
        {'latitude': 6.8649, 'longitude': 79.8997},
        {'latitude': 'invalid', 'longitude': 79.95},
      ],
    });

    expect(geometry.routeId, 'route-1');
    expect(geometry.source, RouteGeometrySource.osrm);
    expect(geometry.cached, isTrue);
    expect(geometry.points, hasLength(2));
    expect(geometry.points.first.latitude, closeTo(6.9271, 0.00001));
    expect(geometry.points.first.longitude, closeTo(79.8612, 0.00001));
  });

  test(
    'builds fallback geometry from depot and sequence-ordered valid stops',
    () {
      final geometry = RouteGeometry.fallbackFor(route);

      expect(geometry.source, RouteGeometrySource.fallback);
      expect(geometry.points, hasLength(3));
      expect(geometry.points[1].latitude, closeTo(6.8649, 0.00001));
      expect(geometry.points[2].latitude, closeTo(6.9061, 0.00001));
    },
  );
}
