import 'package:flutter/material.dart';

import '../../app/fleetopt_driver_app.dart';
import '../../core/routing/app_routes.dart';
import '../../core/theme/app_theme.dart';
import '../alerts/alerts_screen.dart';
import '../route/today_route_screen.dart';
import '../vehicle/vehicle_screen.dart';
import 'home_dashboard.dart';

class DriverShell extends StatelessWidget {
  const DriverShell({super.key});

  @override
  Widget build(BuildContext context) {
    final controller = AppScope.of(context);
    final pages = const [
      HomeDashboard(),
      TodayRouteScreen(),
      AlertsScreen(),
      VehicleScreen(),
    ];

    return AnimatedBuilder(
      animation: controller,
      builder: (context, _) {
        return Scaffold(
          appBar: AppBar(
            title: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'FleetOpt Driver',
                  style: TextStyle(fontWeight: FontWeight.w900),
                ),
                Text(
                  controller.user?.name ?? 'Driver',
                  style: const TextStyle(color: AppColors.muted, fontSize: 12),
                ),
              ],
            ),
            actions: [
              IconButton(
                tooltip: 'Report issue',
                onPressed: () =>
                    Navigator.of(context).pushNamed(AppRoutes.issueReport),
                icon: const Icon(Icons.report_problem_outlined),
              ),
              IconButton(
                tooltip: 'Logout',
                onPressed: controller.logout,
                icon: const Icon(Icons.logout_rounded),
              ),
            ],
          ),
          body: IndexedStack(index: controller.selectedIndex, children: pages),
          bottomNavigationBar: NavigationBar(
            selectedIndex: controller.selectedIndex,
            onDestinationSelected: controller.selectTab,
            destinations: [
              const NavigationDestination(
                icon: Icon(Icons.dashboard_outlined),
                selectedIcon: Icon(Icons.dashboard),
                label: 'Home',
              ),
              const NavigationDestination(
                icon: Icon(Icons.route_outlined),
                selectedIcon: Icon(Icons.route),
                label: 'Route',
              ),
              NavigationDestination(
                icon: Badge(
                  isLabelVisible: controller.activeAlertCount > 0,
                  label: Text('${controller.activeAlertCount}'),
                  child: const Icon(Icons.notifications_outlined),
                ),
                selectedIcon: const Icon(Icons.notifications),
                label: 'Alerts',
              ),
              const NavigationDestination(
                icon: Icon(Icons.local_shipping_outlined),
                selectedIcon: Icon(Icons.local_shipping),
                label: 'Vehicle',
              ),
            ],
          ),
        );
      },
    );
  }
}
