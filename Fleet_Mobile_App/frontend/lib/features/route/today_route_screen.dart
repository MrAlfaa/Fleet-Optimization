import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/theme/app_theme.dart';
import '../../widgets/fleet_widgets.dart';
import 'stop_detail_screen.dart';

class TodayRouteScreen extends StatelessWidget {
  const TodayRouteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        FleetCard(
          padding: EdgeInsets.zero,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                height: 210,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  gradient: const LinearGradient(
                    colors: [Color(0xFF61717F), Color(0xFF95A9B8)],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                ),
                child: Stack(
                  children: [
                    const _MapGrid(),
                    Positioned(
                      left: 28,
                      top: 32,
                      child: _MapMarker(
                        color: AppColors.primary,
                        label: 'Depot',
                      ),
                    ),
                    Positioned(
                      right: 42,
                      top: 62,
                      child: _MapMarker(color: AppColors.critical, label: '1'),
                    ),
                    Positioned(
                      left: 86,
                      bottom: 46,
                      child: _MapMarker(color: AppColors.warning, label: '2'),
                    ),
                    Positioned(
                      right: 86,
                      bottom: 36,
                      child: _MapMarker(color: AppColors.success, label: '4'),
                    ),
                    Positioned(
                      left: 16,
                      right: 16,
                      bottom: 14,
                      child: Row(
                        children: [
                          StatusPill(
                            label: '${controller.route.stops.length} stops',
                            color: AppColors.primary,
                          ),
                          const SizedBox(width: 8),
                          StatusPill(
                            label:
                                '${controller.route.totalDistanceKm.toStringAsFixed(1)} km',
                            color: AppColors.success,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      controller.route.title,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Origin: ${controller.route.depot}',
                      style: const TextStyle(color: AppColors.muted),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Stop order',
          style: Theme.of(
            context,
          ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w900),
        ),
        const SizedBox(height: 10),
        ...controller.route.stops.map(
          (stop) => Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: FleetCard(
              child: InkWell(
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => StopDetailScreen(stopId: stop.id),
                  ),
                ),
                child: Row(
                  children: [
                    CircleAvatar(
                      backgroundColor: AppColors.primary.withValues(
                        alpha: 0.12,
                      ),
                      foregroundColor: AppColors.primary,
                      child: Text(
                        '${stop.sequence}',
                        style: const TextStyle(fontWeight: FontWeight.w900),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            stop.customer,
                            style: const TextStyle(fontWeight: FontWeight.w900),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            '${stop.eta} - ${stop.zone}',
                            style: const TextStyle(color: AppColors.muted),
                          ),
                        ],
                      ),
                    ),
                    StatusPill(
                      label: deliveryStatusLabel(stop.status),
                      color: deliveryStatusColor(stop.status),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _MapGrid extends StatelessWidget {
  const _MapGrid();

  @override
  Widget build(BuildContext context) {
    return CustomPaint(painter: _MapPainter(), size: Size.infinite);
  }
}

class _MapPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withValues(alpha: 0.18)
      ..strokeWidth = 1;
    for (var x = 0.0; x < size.width; x += 28) {
      canvas.drawLine(Offset(x, 0), Offset(x + 120, size.height), paint);
    }
    for (var y = 18.0; y < size.height; y += 34) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y - 60), paint);
    }
    final routePaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 4
      ..strokeCap = StrokeCap.round;
    canvas.drawLine(Offset(44, 52), Offset(size.width - 58, 82), routePaint);
    canvas.drawLine(
      Offset(size.width - 58, 82),
      Offset(112, size.height - 54),
      routePaint,
    );
    canvas.drawLine(
      Offset(112, size.height - 54),
      Offset(size.width - 96, size.height - 44),
      routePaint,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _MapMarker extends StatelessWidget {
  const _MapMarker({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 34,
      height: 34,
      decoration: BoxDecoration(
        color: color,
        shape: BoxShape.circle,
        border: Border.all(color: Colors.white, width: 3),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.22),
            blurRadius: 10,
          ),
        ],
      ),
      alignment: Alignment.center,
      child: Text(
        label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 11,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
