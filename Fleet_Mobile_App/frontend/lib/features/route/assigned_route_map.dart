import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../core/theme/app_theme.dart';
import '../../models/driver_models.dart';

class AssignedRouteMap extends StatelessWidget {
  const AssignedRouteMap({
    super.key,
    required this.route,
    required this.geometry,
    this.currentLocation,
    this.showTiles = true,
  });

  static const tileUserAgentPackageName = 'com.fleetopt.ai.fleetopt_driver';

  final DriverRoute route;
  final RouteGeometry geometry;
  final RouteCoordinate? currentLocation;
  final bool showTiles;

  @override
  Widget build(BuildContext context) {
    final usableGeometry = geometry.hasRenderablePath
        ? geometry
        : RouteGeometry.fallbackFor(route);
    final routePoints = usableGeometry.points
        .map((point) => LatLng(point.latitude, point.longitude))
        .toList(growable: false);
    final boundsPoints = <LatLng>[
      ...routePoints,
      if (currentLocation?.isValid == true)
        LatLng(currentLocation!.latitude, currentLocation!.longitude),
    ];
    final initialCenter = boundsPoints.isNotEmpty
        ? boundsPoints.first
        : const LatLng(6.9271, 79.8612);

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Stack(
        children: [
          Positioned.fill(
            child: ColoredBox(
              color: const Color(0xFFE8EEF0),
              child: FlutterMap(
                options: MapOptions(
                  initialCenter: initialCenter,
                  initialZoom: boundsPoints.length > 1 ? 12 : 13,
                  initialCameraFit: boundsPoints.length > 1
                      ? CameraFit.bounds(
                          bounds: LatLngBounds.fromPoints(boundsPoints),
                          padding: const EdgeInsets.fromLTRB(32, 32, 32, 64),
                        )
                      : null,
                ),
                children: [
                  if (showTiles)
                    TileLayer(
                      urlTemplate:
                          'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: tileUserAgentPackageName,
                      maxZoom: 19,
                    ),
                  if (routePoints.length >= 2)
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: routePoints,
                          strokeWidth: 5,
                          color: AppColors.primary,
                          borderStrokeWidth: 2,
                          borderColor: Colors.white,
                        ),
                      ],
                    ),
                  MarkerLayer(markers: _markers()),
                ],
              ),
            ),
          ),
          Positioned(
            top: 10,
            right: 10,
            child: _MapBadge(
              label: usableGeometry.source == RouteGeometrySource.osrm
                  ? 'Road geometry'
                  : 'Straight-line fallback',
            ),
          ),
          Positioned(
            left: 8,
            right: 8,
            bottom: 8,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.94),
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Text(
                '© OpenStreetMap contributors',
                textAlign: TextAlign.right,
                style: TextStyle(
                  color: AppColors.muted,
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Marker> _markers() {
    final markers = <Marker>[];
    final depot = RouteCoordinate(
      latitude: route.depotLatitude,
      longitude: route.depotLongitude,
    );
    if (depot.isValid) {
      markers.add(
        Marker(
          point: LatLng(depot.latitude, depot.longitude),
          width: 48,
          height: 48,
          child: const _RouteMarker(
            key: Key('route-map-depot-marker'),
            icon: Icons.warehouse_rounded,
            color: AppColors.primary,
            semanticLabel: 'Route depot',
          ),
        ),
      );
    }

    final orderedStops = [...route.stops]
      ..sort((left, right) => left.sequence.compareTo(right.sequence));
    for (final stop in orderedStops) {
      final point = RouteCoordinate(
        latitude: stop.latitude,
        longitude: stop.longitude,
      );
      if (!point.isValid) continue;
      markers.add(
        Marker(
          point: LatLng(point.latitude, point.longitude),
          width: 42,
          height: 42,
          child: _StopMarker(
            key: Key('route-map-stop-${stop.sequence}'),
            sequence: stop.sequence,
            semanticLabel: 'Stop ${stop.sequence}: ${stop.customer}',
          ),
        ),
      );
    }

    if (currentLocation?.isValid == true) {
      markers.add(
        Marker(
          point: LatLng(currentLocation!.latitude, currentLocation!.longitude),
          width: 48,
          height: 48,
          child: const _RouteMarker(
            key: Key('route-map-current-location'),
            icon: Icons.navigation_rounded,
            color: AppColors.success,
            semanticLabel: 'Current driver location',
          ),
        ),
      );
    }
    return markers;
  }
}

class _MapBadge extends StatelessWidget {
  const _MapBadge({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.94),
        borderRadius: BorderRadius.circular(6),
        boxShadow: const [BoxShadow(color: Color(0x22000000), blurRadius: 8)],
      ),
      child: Text(
        label,
        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _RouteMarker extends StatelessWidget {
  const _RouteMarker({
    super.key,
    required this.icon,
    required this.color,
    required this.semanticLabel,
  });

  final IconData icon;
  final Color color;
  final String semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticLabel,
      child: Container(
        decoration: BoxDecoration(
          color: color,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 8)],
        ),
        child: Icon(icon, color: Colors.white, size: 20),
      ),
    );
  }
}

class _StopMarker extends StatelessWidget {
  const _StopMarker({
    super.key,
    required this.sequence,
    required this.semanticLabel,
  });

  final int sequence;
  final String semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: semanticLabel,
      child: Container(
        alignment: Alignment.center,
        decoration: BoxDecoration(
          color: AppColors.critical,
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: const [BoxShadow(color: Color(0x33000000), blurRadius: 8)],
        ),
        child: Text(
          '$sequence',
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w900,
          ),
        ),
      ),
    );
  }
}
