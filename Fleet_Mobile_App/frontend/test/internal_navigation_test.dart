import 'dart:convert';

import 'package:fleetopt_driver/app/fleetopt_driver_app.dart';
import 'package:fleetopt_driver/core/state/app_controller.dart';
import 'package:fleetopt_driver/features/route/fleet_navigation_screen.dart';
import 'package:fleetopt_driver/features/route/today_route_screen.dart';
import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:fleetopt_driver/services/api_client.dart';
import 'package:fleetopt_driver/services/driver_api_service.dart';
import 'package:fleetopt_driver/services/location_service.dart';
import 'package:fleetopt_driver/services/mock_auth_service.dart';
import 'package:fleetopt_driver/services/mock_driver_service.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

class _NavigationDriverService extends MockDriverService {
  String? startedStopId;

  @override
  Future<DriverNavigationState> startStopNavigation(String orderId) async {
    startedStopId = orderId;
    return super.startStopNavigation(orderId);
  }
}

class _UnavailableLocationService extends DriverLocationService {
  @override
  Future<DriverLocationUpdate?> getCurrentLocation() async => null;
}

void main() {
  test('navigation API starts the selected stop inside FleetOpt', () async {
    late http.Request request;
    final service = DriverApiService(
      apiClient: ApiClient(
        client: MockClient((value) async {
          request = value;
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {
                'current_stop_id': 'stop-1',
                'current_parcel_code': 'QA-PARCEL-001',
                'current_customer_name': 'District Center Alpha',
                'status': 'navigating',
                'started_at': '2026-08-29T04:15:00Z',
              },
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
        baseUrl: 'http://localhost:8000/api',
        tokenProvider: () => 'driver-token',
      ),
    );

    final state = await service.startStopNavigation('stop-1');

    expect(request.method, 'POST');
    expect(request.url.path, '/api/driver/deliveries/stop-1/navigation/start');
    expect(state.currentParcelCode, 'QA-PARCEL-001');
    expect(state.isNavigating, isTrue);
  });

  testWidgets('route action opens FleetOpt internal navigation', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(720, 1531);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final service = _NavigationDriverService();
    final controller = AppController(
      authService: MockAuthService(),
      driverService: service,
      locationService: _UnavailableLocationService(),
    );
    await controller.refreshDriverData();
    controller.tripActive = true;

    await tester.pumpWidget(
      AppScope(
        controller: controller,
        child: const MaterialApp(home: Scaffold(body: TodayRouteScreen())),
      ),
    );

    expect(find.text('Open full route in Google Maps'), findsNothing);
    await tester.scrollUntilVisible(
      find.text('Open FleetOpt route navigator'),
      180,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Open FleetOpt route navigator'), findsOneWidget);

    await tester.scrollUntilVisible(
      find.text('Start FleetOpt navigation'),
      -180,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.tap(find.text('Start FleetOpt navigation'));
    await tester.pumpAndSettle();

    expect(service.startedStopId, 'stop-1');
    expect(find.byType(FleetNavigationScreen), findsOneWidget);
    expect(find.text('FleetOpt navigation'), findsOneWidget);
    expect(find.textContaining('QA-PARCEL-001'), findsWidgets);

    expect(find.text('Mark arrived'), findsOneWidget);
    await tester.tap(find.text('Mark arrived'));
    await tester.pumpAndSettle();

    expect(find.text('ARRIVED'), findsOneWidget);
    expect(find.text('Confirm parcel delivered'), findsOneWidget);
  });
}
