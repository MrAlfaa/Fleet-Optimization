import 'package:flutter/material.dart';

import 'app/fleetopt_driver_app.dart';
import 'core/state/app_controller.dart';
import 'services/mock_auth_service.dart';
import 'services/mock_driver_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final controller = AppController(
    authService: MockAuthService(),
    driverService: MockDriverService(),
  );
  await controller.restoreSession();
  runApp(FleetOptDriverApp(controller: controller));
}
