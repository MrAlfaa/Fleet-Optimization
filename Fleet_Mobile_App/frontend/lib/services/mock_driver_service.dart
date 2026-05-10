import '../models/driver_models.dart';

class MockDriverService {
  AssignedVehicle getAssignedVehicle() {
    return const AssignedVehicle(
      id: 'veh-492',
      number: 'TRK-492',
      model: 'Volvo VNL',
      type: 'Heavy Truck',
      mileage: 142500,
      riskLevel: 'medium',
      riskSummary:
          'Brake pads show elevated wear. Avoid extended high-load dispatch.',
      modelStatus: 'Placeholder baseline',
    );
  }

  DriverRoute getTodayRoute() {
    return const DriverRoute(
      id: 'route-7a',
      title: 'Route 7A - Colombo East',
      depot: 'Port 4 Distribution Hub',
      totalDistanceKm: 86.4,
      eta: '14:30',
      stops: [
        RouteStop(
          id: 'stop-1',
          sequence: 1,
          customer: 'District Center Alpha',
          address: '220 Lake Drive, Colombo Central',
          zone: 'Colombo Central',
          eta: '09:20',
          priority: 'Critical',
          latitude: 6.9271,
          longitude: 79.8612,
          status: DeliveryStatus.pending,
        ),
        RouteStop(
          id: 'stop-2',
          sequence: 2,
          customer: 'Nugegoda Medical Stores',
          address: '45 High Level Road, Nugegoda',
          zone: 'Nugegoda',
          eta: '10:40',
          priority: 'High',
          latitude: 6.8649,
          longitude: 79.8997,
          status: DeliveryStatus.pending,
        ),
        RouteStop(
          id: 'stop-3',
          sequence: 3,
          customer: 'Malabe Fulfillment Point',
          address: '310 IT Park Avenue, Malabe',
          zone: 'Malabe',
          eta: '12:15',
          priority: 'Standard',
          latitude: 6.9061,
          longitude: 79.9696,
          status: DeliveryStatus.pending,
        ),
        RouteStop(
          id: 'stop-4',
          sequence: 4,
          customer: 'Kaduwela Retail Hub',
          address: '88 Riverside Road, Kaduwela',
          zone: 'Kaduwela',
          eta: '13:45',
          priority: 'Standard',
          latitude: 6.9358,
          longitude: 79.9842,
          status: DeliveryStatus.pending,
        ),
      ],
    );
  }

  List<DriverAlert> getAlerts() {
    return const [
      DriverAlert(
        id: 'alert-1',
        title: 'Maintenance Risk Warning',
        message:
            'TRK-492 brake risk remains medium. Complete route and report abnormal vibration.',
        category: 'Maintenance',
        severity: AlertSeverity.warning,
        timestamp: '08:10 AM',
        acknowledged: false,
      ),
      DriverAlert(
        id: 'alert-2',
        title: 'Weather Watch',
        message:
            'Rain expected near Malabe after 12:00. Planner recommends keeping Route 7A order.',
        category: 'Weather',
        severity: AlertSeverity.info,
        timestamp: '08:25 AM',
        acknowledged: false,
      ),
      DriverAlert(
        id: 'alert-3',
        title: 'Priority Delivery',
        message: 'District Center Alpha must be completed before 09:45.',
        category: 'Route',
        severity: AlertSeverity.critical,
        timestamp: '08:32 AM',
        acknowledged: false,
      ),
    ];
  }

  List<TripEvent> getTripEvents() {
    return const [
      TripEvent(
        time: '08:00',
        title: 'Pre-trip inspection cleared',
        description:
            'Vehicle condition accepted with medium brake-risk notice.',
        type: AlertSeverity.info,
      ),
      TripEvent(
        time: '08:15',
        title: 'Route assigned',
        description: 'Route 7A synced from planner dashboard placeholder data.',
        type: AlertSeverity.info,
      ),
    ];
  }
}
