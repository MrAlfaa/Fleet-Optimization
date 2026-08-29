import 'package:fleetopt_driver/features/trip/trip_inspection_sheet.dart';
import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  Future<void> openPreTripSheet(
    WidgetTester tester,
    AssignedVehicle vehicle,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Builder(
          builder: (context) => ElevatedButton(
            onPressed: () => showPreTripInspectionSheet(
              context,
              initialMileage: vehicle.mileage.toDouble(),
              vehicle: vehicle,
            ),
            child: const Text('Open inspection'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Open inspection'));
    await tester.pumpAndSettle();
  }

  Future<void> openPostTripSheet(
    WidgetTester tester,
    AssignedVehicle vehicle, {
    double bottomSystemInset = 0,
  }) async {
    await tester.pumpWidget(
      MaterialApp(
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(
            context,
          ).copyWith(viewPadding: EdgeInsets.only(bottom: bottomSystemInset)),
          child: child!,
        ),
        home: Builder(
          builder: (context) => ElevatedButton(
            onPressed: () => showPostTripInspectionSheet(
              context,
              initialMileage: vehicle.mileage.toDouble(),
              vehicle: vehicle,
            ),
            child: const Text('Open post-trip inspection'),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Open post-trip inspection'));
    await tester.pumpAndSettle();
  }

  testWidgets('diesel pre-trip inspection uses fuel context without battery', (
    tester,
  ) async {
    const vehicle = AssignedVehicle(
      id: 'diesel-1',
      number: 'WP LO-2411',
      model: 'Isuzu N-Series',
      type: 'diesel_truck',
      category: 'truck',
      fuelType: 'diesel',
      mileage: 83000,
      riskLevel: 'low',
      riskSummary: 'Ready',
      modelStatus: 'Available',
    );

    await openPreTripSheet(tester, vehicle);

    expect(find.text('Battery charge - SoC (%)'), findsNothing);
    await tester.drag(find.byType(Scrollable).last, const Offset(0, -220));
    await tester.pumpAndSettle();
    expect(find.text('Fuel system condition'), findsOneWidget);
    expect(find.text('Engine and drivetrain condition'), findsOneWidget);
  });

  testWidgets('electric pre-trip inspection shows optional battery context', (
    tester,
  ) async {
    const vehicle = AssignedVehicle(
      id: 'ev-1',
      number: 'WP CAA-1234',
      model: 'Electric Van',
      type: 'electric_van',
      category: 'van',
      fuelType: 'electric',
      mileage: 42000,
      riskLevel: 'low',
      riskSummary: 'Ready',
      modelStatus: 'Available',
    );

    await openPreTripSheet(tester, vehicle);

    expect(find.text('Battery charge - SoC (%) (optional)'), findsOneWidget);
    await tester.drag(find.byType(Scrollable).last, const Offset(0, -220));
    await tester.pumpAndSettle();
    expect(find.text('Charging system condition'), findsOneWidget);
    expect(find.text('Electric drivetrain condition'), findsOneWidget);
  });

  testWidgets('inspection form keeps submit action above system navigation', (
    tester,
  ) async {
    const vehicle = AssignedVehicle(
      id: 'ev-1',
      number: 'WP CAA-1234',
      model: 'Electric Van',
      type: 'electric_van',
      category: 'van',
      fuelType: 'electric',
      mileage: 42000,
      riskLevel: 'low',
      riskSummary: 'Ready',
      modelStatus: 'Available',
    );

    await openPostTripSheet(tester, vehicle, bottomSystemInset: 64);

    final listView = tester.widget<ListView>(
      find.byKey(const ValueKey('inspection-form-scroll')),
    );
    final padding = listView.padding!.resolve(TextDirection.ltr);
    expect(padding.bottom, 24);
    expect(find.text('Submit inspection'), findsOneWidget);
    expect(
      tester.getRect(find.text('Submit inspection')).bottom,
      lessThan(736),
    );
  });
}
