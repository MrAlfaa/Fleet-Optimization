import 'package:fleetopt_driver/features/route/assigned_route_map.dart';
import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('uses the Android application id for OSM tile identification', () {
    expect(
      AssignedRouteMap.tileUserAgentPackageName,
      'com.fleetopt.ai.fleetopt_driver',
    );
  });

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

  testWidgets('renders route markers, current location and OSM attribution', (
    tester,
  ) async {
    final geometry = RouteGeometry.fallbackFor(route);
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: SizedBox(
            height: 260,
            child: AssignedRouteMap(
              route: route,
              geometry: geometry,
              currentLocation: const RouteCoordinate(
                latitude: 6.90,
                longitude: 79.88,
              ),
              showTiles: false,
            ),
          ),
        ),
      ),
    );
    await tester.pump();

    expect(find.byKey(const Key('route-map-depot-marker')), findsOneWidget);
    expect(find.byKey(const Key('route-map-stop-1')), findsOneWidget);
    expect(find.byKey(const Key('route-map-current-location')), findsOneWidget);
    expect(find.text('© OpenStreetMap contributors'), findsOneWidget);
    expect(find.text('Straight-line fallback'), findsOneWidget);
  });
}
