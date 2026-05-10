import 'package:flutter/material.dart';

import '../core/routing/app_routes.dart';
import '../core/state/app_controller.dart';
import '../core/theme/app_theme.dart';
import '../features/auth/login_screen.dart';
import '../features/auth/register_screen.dart';
import '../features/home/driver_shell.dart';
import '../features/issues/issue_report_screen.dart';

class FleetOptDriverApp extends StatelessWidget {
  const FleetOptDriverApp({super.key, required this.controller});

  final AppController controller;

  @override
  Widget build(BuildContext context) {
    return AppScope(
      controller: controller,
      child: AnimatedBuilder(
        animation: controller,
        builder: (context, _) {
          return MaterialApp(
            title: 'FleetOpt Driver',
            debugShowCheckedModeBanner: false,
            theme: AppTheme.light(),
            home: controller.isAuthenticated
                ? const DriverShell()
                : const LoginScreen(),
            routes: {
              AppRoutes.login: (_) => const LoginScreen(),
              AppRoutes.register: (_) => const RegisterScreen(),
              AppRoutes.issueReport: (_) => const IssueReportScreen(),
            },
          );
        },
      ),
    );
  }
}

class AppScope extends InheritedWidget {
  const AppScope({super.key, required this.controller, required super.child});

  final AppController controller;

  static AppController of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope is missing from the widget tree');
    return scope!.controller;
  }

  @override
  bool updateShouldNotify(AppScope oldWidget) =>
      controller != oldWidget.controller;
}
