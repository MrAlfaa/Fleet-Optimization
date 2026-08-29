import 'dart:convert';

import 'package:fleetopt_driver/services/api_client.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

void main() {
  test(
    'refreshes an expired driver token and retries the request once',
    () async {
      var token = 'expired-token';
      var requests = 0;
      var refreshes = 0;
      final client = ApiClient(
        baseUrl: 'http://localhost:8000/api',
        tokenProvider: () => token,
        client: MockClient((request) async {
          requests += 1;
          if (request.headers['authorization'] == 'Bearer expired-token') {
            return http.Response(jsonEncode({'detail': 'Expired token'}), 401);
          }
          return http.Response(
            jsonEncode({
              'success': true,
              'data': {'status': 'ok'},
            }),
            200,
            headers: {'content-type': 'application/json'},
          );
        }),
      );
      client.onUnauthorized = () async {
        refreshes += 1;
        token = 'fresh-token';
        return true;
      };

      final result = await client.get<Map<String, dynamic>>(
        '/driver/assigned-route',
      );

      expect(result['status'], 'ok');
      expect(refreshes, 1);
      expect(requests, 2);
    },
  );

  test(
    'does not clear or refresh a valid session for forbidden requests',
    () async {
      var refreshes = 0;
      final client = ApiClient(
        baseUrl: 'http://localhost:8000/api',
        tokenProvider: () => 'valid-token',
        client: MockClient(
          (_) async => http.Response(jsonEncode({'detail': 'Forbidden'}), 403),
        ),
      );
      client.onUnauthorized = () async {
        refreshes += 1;
        return false;
      };

      await expectLater(
        client.get<Map<String, dynamic>>('/admin-only'),
        throwsA(
          isA<ApiException>().having(
            (error) => error.statusCode,
            'status',
            403,
          ),
        ),
      );
      expect(refreshes, 0);
    },
  );
}
