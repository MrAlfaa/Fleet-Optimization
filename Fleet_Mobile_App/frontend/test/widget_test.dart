import 'package:fleetopt_driver/app/fleetopt_driver_app.dart';
import 'package:fleetopt_driver/core/state/app_controller.dart';
import 'package:fleetopt_driver/services/mock_auth_service.dart';
import 'package:fleetopt_driver/services/mock_driver_service.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  Future<AppController> buildController() async {
    SharedPreferences.setMockInitialValues({});
    final controller = AppController(
      authService: MockAuthService(),
      driverService: MockDriverService(),
    );
    await controller.restoreSession();
    return controller;
  }

  testWidgets('driver can login and see assigned route dashboard', (
    tester,
  ) async {
    final controller = await buildController();
    await tester.pumpWidget(FleetOptDriverApp(controller: controller));

    expect(find.text('Driver sign in'), findsOneWidget);

    await tester.drag(find.byType(Scrollable).first, const Offset(0, -280));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    expect(find.text('FleetOpt Driver'), findsOneWidget);
    expect(find.text('Route 7A - Colombo East'), findsOneWidget);
  });

  testWidgets('driver can open route and update a delivery stop', (
    tester,
  ) async {
    final controller = await buildController();
    await tester.pumpWidget(FleetOptDriverApp(controller: controller));
    await tester.drag(find.byType(Scrollable).first, const Offset(0, -280));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Route'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('District Center Alpha'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delivered'));
    await tester.pumpAndSettle();

    expect(controller.route.completedStops, 1);
  });
}
