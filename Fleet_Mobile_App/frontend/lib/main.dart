import 'package:flutter/material.dart';

import 'app/fleetopt_driver_app.dart';
import 'core/state/app_controller.dart';
import 'services/api_client.dart';
import 'services/auth_api_service.dart';
import 'services/driver_api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final apiClient = ApiClient();
  final authService = AuthApiService(apiClient: apiClient);
  apiClient.tokenProvider = () => authService.accessToken;
  final controller = AppController(
    authService: authService,
    driverService: DriverApiService(apiClient: apiClient),
  );
  apiClient.onUnauthorized = controller.handleDeviceRevoked;
  await controller.restoreSession();
  runApp(FleetOptDriverApp(controller: controller));
}
