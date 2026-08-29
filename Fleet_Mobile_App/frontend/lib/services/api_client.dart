import 'dart:convert';

import 'package:http/http.dart' as http;

typedef TokenProvider = String? Function();
typedef UnauthorizedHandler = Future<bool> Function();

class ApiException implements Exception {
  const ApiException({
    required this.message,
    required this.statusCode,
    this.data,
  });

  final String message;
  final int statusCode;
  final Object? data;

  @override
  String toString() => message;
}

class ApiClient {
  ApiClient({http.Client? client, String? baseUrl, this.tokenProvider})
    : _client = client ?? http.Client(),
      baseUrl = (baseUrl ?? _defaultBaseUrl).replaceAll(RegExp(r'/+$'), '');

  static const _defaultBaseUrl = String.fromEnvironment(
    'FLEETOPT_API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api',
  );

  final http.Client _client;
  final String baseUrl;
  TokenProvider? tokenProvider;
  UnauthorizedHandler? onUnauthorized;

  Future<T> get<T>(String path) {
    return _send<T>('GET', path);
  }

  Future<T> post<T>(
    String path,
    Map<String, dynamic> body, {
    bool retryUnauthorized = true,
  }) {
    return _send<T>(
      'POST',
      path,
      body: body,
      retryUnauthorized: retryUnauthorized,
    );
  }

  Future<T> patch<T>(String path, Map<String, dynamic> body) {
    return _send<T>('PATCH', path, body: body);
  }

  Future<T> _send<T>(
    String method,
    String path, {
    Map<String, dynamic>? body,
    bool retryUnauthorized = true,
  }) async {
    final uri = Uri.parse('$baseUrl${path.startsWith('/') ? path : '/$path'}');
    final token = tokenProvider?.call();
    final headers = <String, String>{
      'Content-Type': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Bearer $token',
    };

    late http.Response response;
    try {
      response = switch (method) {
        'GET' => await _client.get(uri, headers: headers),
        'POST' => await _client.post(
          uri,
          headers: headers,
          body: jsonEncode(body ?? const <String, dynamic>{}),
        ),
        'PATCH' => await _client.patch(
          uri,
          headers: headers,
          body: jsonEncode(body ?? const <String, dynamic>{}),
        ),
        _ => throw ArgumentError('Unsupported API method $method'),
      };
    } on http.ClientException catch (error) {
      throw ApiException(
        statusCode: 0,
        message: 'Unable to reach FleetOpt API. Check backend connection.',
        data: error.message,
      );
    }

    final decoded = _decodeResponse(response);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      if (response.statusCode == 401 &&
          token != null &&
          retryUnauthorized &&
          onUnauthorized != null &&
          await onUnauthorized!.call()) {
        return _send<T>(method, path, body: body, retryUnauthorized: false);
      }
      throw ApiException(
        statusCode: response.statusCode,
        message: _messageFrom(decoded) ?? 'FleetOpt API request failed.',
        data: decoded,
      );
    }

    if (decoded is Map<String, dynamic> && decoded.containsKey('success')) {
      if (decoded['success'] == false) {
        throw ApiException(
          statusCode: response.statusCode,
          message: _messageFrom(decoded) ?? 'FleetOpt API request failed.',
          data: decoded['data'],
        );
      }
      return decoded['data'] as T;
    }

    return decoded as T;
  }

  Object? _decodeResponse(http.Response response) {
    if (response.body.trim().isEmpty) {
      return null;
    }
    try {
      return jsonDecode(response.body);
    } catch (_) {
      throw ApiException(
        statusCode: response.statusCode,
        message: 'FleetOpt API returned an invalid response.',
        data: response.body,
      );
    }
  }

  String? _messageFrom(Object? decoded) {
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];
      if (detail is String && detail.isNotEmpty) {
        return detail;
      }
      if (detail is List && detail.isNotEmpty) {
        return detail
            .map((item) {
              if (item is Map && item['msg'] != null) {
                return item['msg'].toString();
              }
              return item.toString();
            })
            .join(', ');
      }
      final message = decoded['message'];
      if (message is String && message.isNotEmpty) {
        return message;
      }
    }
    return null;
  }
}
