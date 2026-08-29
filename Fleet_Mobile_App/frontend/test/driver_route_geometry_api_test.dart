import 'dart:convert';

import 'package:fleetopt_driver/services/api_client.dart';
import 'package:fleetopt_driver/services/driver_api_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('loads route geometry from the authenticated route endpoint', () async {
    late Uri requestedUri;
    final client = MockClient((request) async {
      requestedUri = request.url;
      return http.Response(
        jsonEncode({
          'success': true,
          'data': {
            'route_id': 'route-1',
            'geometry_source': 'osrm',
            'cached': false,
            'coordinates': [
              {'latitude': 6.9271, 'longitude': 79.8612},
              {'latitude': 6.8649, 'longitude': 79.8997},
            ],
          },
        }),
        200,
        headers: {'content-type': 'application/json'},
      );
    });
    final service = DriverApiService(
      apiClient: ApiClient(
        client: client,
        baseUrl: 'http://localhost:8000/api',
        tokenProvider: () => 'driver-token',
      ),
    );

    final geometry = await service.getRouteGeometry('route-1');

    expect(requestedUri.path, '/api/routes/route-1/geometry');
    expect(geometry.points, hasLength(2));
    expect(geometry.source.name, 'osrm');
  });
}
