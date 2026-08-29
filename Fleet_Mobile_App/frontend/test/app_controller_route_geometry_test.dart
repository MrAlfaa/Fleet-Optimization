import 'package:fleetopt_driver/core/state/app_controller.dart';
import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:fleetopt_driver/services/mock_auth_service.dart';
import 'package:fleetopt_driver/services/mock_driver_service.dart';
import 'package:flutter_test/flutter_test.dart';

class _FailingGeometryService extends MockDriverService {
  bool geometryRequested = false;

  @override
  Future<RouteGeometry> getRouteGeometry(String routeId) async {
    geometryRequested = true;
    throw StateError('OSRM unavailable');
  }
}

void main() {
  test(
    'route refresh retains a renderable fallback when geometry fails',
    () async {
      final service = _FailingGeometryService();
      final controller = AppController(
        authService: MockAuthService(),
        driverService: service,
      );

      await controller.refreshDriverData();

      expect(service.geometryRequested, isTrue);
      expect(controller.routeGeometry.source, RouteGeometrySource.fallback);
      expect(controller.routeGeometry.hasRenderablePath, isTrue);
    },
  );
}
