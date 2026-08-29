import 'package:fleetopt_driver/app/fleetopt_driver_app.dart';
import 'package:fleetopt_driver/core/state/app_controller.dart';
import 'package:fleetopt_driver/services/mock_auth_service.dart';
import 'package:fleetopt_driver/services/mock_driver_service.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Future<AppController> buildController() async {
    final controller = AppController(
      authService: MockAuthService(),
      driverService: MockDriverService(),
    );
    await controller.restoreSession();
    return controller;
  }

  Future<void> enrollAndSetup(WidgetTester tester) async {
    await tester.enterText(find.byType(EditableText).at(0), 'driver.demo');
    await tester.enterText(find.byType(EditableText).at(1), 'Temporary@123');
    await tester.drag(find.byType(Scrollable).first, const Offset(0, -280));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Register device'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(EditableText).at(0), '123456');
    await tester.enterText(find.byType(EditableText).at(1), '123456');
    await tester.drag(find.byType(Scrollable).first, const Offset(0, -200));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Complete secure registration'));
    await tester.pumpAndSettle();
  }

  testWidgets('driver can enroll and see assigned route dashboard', (
    tester,
  ) async {
    final controller = await buildController();
    await tester.pumpWidget(FleetOptDriverApp(controller: controller));

    expect(find.text('Register this driver device'), findsOneWidget);
    await enrollAndSetup(tester);

    expect(find.text('FleetOpt Driver'), findsOneWidget);
    expect(find.text('Route 7A - Colombo East'), findsOneWidget);
  });

  testWidgets('driver with an active trip can update the next delivery stop', (
    tester,
  ) async {
    final controller = await buildController();
    await tester.pumpWidget(FleetOptDriverApp(controller: controller));
    await enrollAndSetup(tester);
    controller.tripActive = true;
    await tester.pump();

    await tester.tap(find.text('Route'));
    await tester.pumpAndSettle();
    expect(find.text('© OpenStreetMap contributors'), findsOneWidget);
    expect(find.textContaining('Parcel QA-PARCEL-001'), findsOneWidget);
    final firstStop = find.text('District Center Alpha').last;
    await tester.ensureVisible(firstStop);
    await tester.pumpAndSettle();
    await tester.tap(firstStop);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Delivered'));
    await tester.pumpAndSettle();

    expect(controller.route.completedStops, 1);
  });

  testWidgets('vehicle tab shows powertrain-aware inspection requirements', (
    tester,
  ) async {
    final controller = await buildController();
    await tester.pumpWidget(FleetOptDriverApp(controller: controller));
    await enrollAndSetup(tester);

    await tester.tap(find.text('Vehicle'));
    await tester.pumpAndSettle();

    expect(find.text('diesel'), findsOneWidget);
    await tester.drag(find.byType(Scrollable).last, const Offset(0, -360));
    await tester.pumpAndSettle();
    expect(find.text('Engine and drivetrain condition'), findsOneWidget);
    expect(find.text('Fuel system condition'), findsOneWidget);
    expect(find.text('Battery charge (operational context)'), findsNothing);
  });
}
