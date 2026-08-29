import 'dart:convert';

import 'package:fleetopt_driver/models/driver_models.dart';
import 'package:fleetopt_driver/services/api_client.dart';
import 'package:fleetopt_driver/services/driver_api_service.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test('posts canonical sensor-free pre-trip observation payload', () async {
    late Map<String, dynamic> requestBody;
    final service = DriverApiService(
      apiClient: ApiClient(
        client: MockClient((request) async {
          requestBody = jsonDecode(request.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {
                'id': 'inspection-1',
                'safe_to_operate': true,
                'blocking_reasons': <String>[],
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

    await service.submitPreTripInspection(
      const PreTripInspection(
        odometer: 83000,
        tireCondition: 'normal',
        brakeCondition: 'warning',
        powertrainCondition: 'normal',
        chargingOrFuelIssue: 'none',
        vehicleDamage: 'none',
        dashboardWarning: 'none',
        unusualNoise: 'mild',
        vibrationLevel: 'none',
      ),
    );

    expect(requestBody['odometer'], 83000.0);
    expect(requestBody['powertrain_condition'], 'normal');
    expect(requestBody['charging_or_fuel_issue'], 'none');
    expect(requestBody.containsKey('battery_soc'), isFalse);
    expect(requestBody.containsKey('failure_probability'), isFalse);
  });
}
