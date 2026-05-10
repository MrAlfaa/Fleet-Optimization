import type {
  Alert,
  DemandForecast,
  DemandZone,
  DeliveryOrder,
  MaintenanceRecord,
  RoutePlan,
  TripEvent,
  User,
  Vehicle,
  VehiclePart,
} from '../types'

export const demoUser: User = {
  id: 'usr-001',
  name: 'Dhananjaya Kumara',
  email: 'manager@fleetopt.ai',
  role: 'fleet_manager',
  organization: 'FleetOpt AI Research Lab',
}

export const vehicles: Vehicle[] = [
  {
    id: 'cab-1024',
    number: 'CAB-1024',
    model: 'Freightliner Cascadia',
    type: 'Heavy Truck',
    assignedDriver: 'Nimal Perera',
    mileage: 120450,
    status: 'Active',
    risk: 'low',
    route: 'Route 4A',
  },
  {
    id: 'trk-2041',
    number: 'TRK-2041',
    model: 'Volvo VNL',
    type: 'Heavy Truck',
    assignedDriver: 'Kasun Silva',
    mileage: 85200,
    status: 'Active',
    risk: 'medium',
    route: 'Route 2B',
  },
  {
    id: 'van-3810',
    number: 'VAN-3810',
    model: 'Ford Transit',
    type: 'Light Van',
    assignedDriver: 'Amali Fernando',
    mileage: 45100,
    status: 'Maintenance',
    risk: 'high',
  },
  {
    id: 'cab-1028',
    number: 'CAB-1028',
    model: 'Peterbilt 579',
    type: 'Heavy Truck',
    assignedDriver: 'Dinesh Kumar',
    mileage: 210000,
    status: 'In Transit',
    risk: 'critical',
    route: 'Route 7A',
  },
]

export const vehicleParts: VehiclePart[] = [
  { id: 'engine', vehicleId: 'cab-1024', name: 'Engine', lastService: '12 Oct 2023', failures: 1, risk: 'medium', predictedNext: 'In 14 days', note: 'Combustion timing variance rising under heavy loads.' },
  { id: 'battery', vehicleId: 'cab-1024', name: 'Battery', lastService: '05 Jan 2024', failures: 0, risk: 'low', predictedNext: 'In 180 days', note: 'Voltage profile stable across recent trips.' },
  { id: 'brakes', vehicleId: 'cab-1024', name: 'Brake Pads', lastService: '22 May 2023', failures: 2, risk: 'critical', predictedNext: 'Overdue by 5 days', note: 'Critical wear detected through service history baseline.' },
  { id: 'tires', vehicleId: 'cab-1024', name: 'Tires', lastService: '10 Nov 2023', failures: 0, risk: 'medium', predictedNext: 'In 30 days', note: 'Rear-right tire pressure drift needs inspection.' },
  { id: 'suspension', vehicleId: 'cab-1024', name: 'Suspension', lastService: '01 Sep 2023', failures: 0, risk: 'low', predictedNext: 'In 120 days', note: 'No abnormal vibration events recorded.' },
  { id: 'oil', vehicleId: 'cab-1024', name: 'Oil Filter', lastService: '15 Aug 2023', failures: 0, risk: 'medium', predictedNext: 'In 7 days', note: 'Service recommended before high-demand week.' },
  { id: 'clutch', vehicleId: 'cab-1024', name: 'Clutch', lastService: '12 Feb 2022', failures: 0, risk: 'low', predictedNext: 'In 210 days', note: 'No slip events logged in current cycle.' },
  { id: 'radiator', vehicleId: 'cab-1024', name: 'Radiator', lastService: '04 Apr 2023', failures: 0, risk: 'low', predictedNext: 'In 95 days', note: 'Temperature curve stable after last service.' },
  { id: 'lights', vehicleId: 'cab-1024', name: 'Lights', lastService: '20 Dec 2023', failures: 1, risk: 'low', predictedNext: 'In 60 days', note: 'Left unit replaced during last inspection.' },
]

export const maintenanceRecords: MaintenanceRecord[] = [
  { id: 'mnt-1', date: 'Oct 24, 2023', vehicle: 'TRK-2041', service: 'Brake Pad Replacement', technician: 'M. Jenkins', cost: '$845.00', status: 'Overdue' },
  { id: 'mnt-2', date: 'Oct 22, 2023', vehicle: 'VAN-3810', service: 'Transmission Fluid Flush', technician: 'S. Carter', cost: '$320.00', status: 'Overdue' },
  { id: 'mnt-3', date: 'Oct 20, 2023', vehicle: 'CAB-1024', service: 'PM A-Service', technician: 'J. Davis', cost: '$450.00', status: 'Completed' },
  { id: 'mnt-4', date: 'Oct 18, 2023', vehicle: 'VAN-118', service: 'Tire Rotation & Balance', technician: 'Ext. Vendor', cost: '$120.00', status: 'Completed' },
  { id: 'mnt-5', date: 'Oct 15, 2023', vehicle: 'TRK-501', service: 'DEF System Diagnostic', technician: 'M. Jenkins', cost: '$--', status: 'Pending Parts' },
]

export const deliveries: DeliveryOrder[] = [
  { id: 'ord-9921-a', customer: 'Acme Corp', priority: 'Critical', timeWindow: '08:00 AM - 10:00 AM', zone: 'Colombo Central', location: '1240 Industrial Pkwy, Suite 100', status: 'Unassigned' },
  { id: 'ord-9922-b', customer: 'Global Logistics Inc.', priority: 'Standard', timeWindow: '11:00 AM - 02:00 PM', zone: 'Nugegoda', location: '880 Logistics Blvd, Warehouse 4', status: 'Routed' },
  { id: 'ord-9923-c', customer: 'TechWorks LLC', priority: 'High', timeWindow: '09:30 AM - 11:30 AM', zone: 'Malabe', location: '400 Innovation Drive, Building B', status: 'In Transit' },
  { id: 'ord-9924-d', customer: 'City Hospital', priority: 'Critical', timeWindow: 'Anytime', zone: 'Dehiwala', location: '100 Health Way, Loading Dock C', status: 'Unassigned' },
  { id: 'ord-9925-e', customer: 'Retail Hub', priority: 'High', timeWindow: '01:00 PM - 03:00 PM', zone: 'Kaduwela', location: '52 Commerce Street', status: 'Unassigned' },
]

export const demandZones: DemandZone[] = [
  { id: 'zone-1', name: 'Colombo Central', predicted: 5800, actual: 4250, overloadScore: 124, risk: 'critical' },
  { id: 'zone-2', name: 'Nugegoda', predicted: 2350, actual: 2100, overloadScore: 95, risk: 'high' },
  { id: 'zone-3', name: 'Dehiwala', predicted: 1800, actual: 1850, overloadScore: 42, risk: 'low' },
  { id: 'zone-4', name: 'Malabe', predicted: 1100, actual: 950, overloadScore: 64, risk: 'medium' },
  { id: 'zone-5', name: 'Kaduwela', predicted: 1250, actual: 1180, overloadScore: 58, risk: 'medium' },
]

export const demandForecasts: DemandForecast[] = [
  { zone: 'Colombo Central', currentVolume: 4250, predictedVolume: 5800, variance: 36.4, action: 'Allocate +12 vans' },
  { zone: 'Nugegoda', currentVolume: 2100, predictedVolume: 2350, variance: 11.9, action: 'Monitor capacity' },
  { zone: 'Dehiwala', currentVolume: 1850, predictedVolume: 1800, variance: -2.7, action: 'No action required' },
  { zone: 'Malabe', currentVolume: 950, predictedVolume: 1100, variance: 15.7, action: 'Pre-position 2 units' },
]

export const routePlan: RoutePlan = {
  id: 'route-7a',
  vehicle: 'VAN-3810',
  driver: 'Amali Fernando',
  distance: '142.8 km',
  eta: '5h 12m',
  capacityUse: 88,
  warning: 'Vehicle VAN-3810 is flagged for overdue brake maintenance. Assign a lower workload route or override with reason.',
  stops: [
    { sequence: 1, name: 'Warehouse Alpha', eta: '08:15 AM', loadDrop: '--', status: 'Origin' },
    { sequence: 2, name: 'TechSolutions Inc.', eta: '09:30 AM', loadDrop: '400 kg', status: 'Pending' },
    { sequence: 3, name: 'Global Retail Hub', eta: '10:45 AM', loadDrop: '1,200 kg', status: 'Pending' },
    { sequence: 4, name: 'City Center Offices', eta: '11:50 AM', loadDrop: '150 kg', status: 'Pending' },
  ],
}

export const tripEvents: TripEvent[] = [
  { id: 'trip-1', time: '10:15 AM', title: 'Crossed Checkpoint Charlie', description: 'Maintaining steady speed. No anomalies detected.', severity: 'info' },
  { id: 'trip-2', time: '09:42 AM', title: 'Traffic Delay Detected', description: 'Route re-optimization suggested. +15m impact.', severity: 'warning' },
  { id: 'trip-3', time: '08:00 AM', title: 'Departed Origin', description: 'Pre-trip inspection cleared.', severity: 'info' },
]

export const alerts: Alert[] = [
  { id: 'al-1', time: '08:42 AM', title: 'Engine Temperature Exceeds Safe Threshold', description: 'Immediate pull-over recommended. Engine shutdown imminent.', severity: 'critical', category: 'maintenance', vehicle: 'CAB-1028', acknowledged: false },
  { id: 'al-2', time: '08:15 AM', title: 'Major Highway Closure Detected', description: '3 fleets currently on trajectory. Re-routing required immediately.', severity: 'critical', category: 'route', vehicle: 'RTE-89B', acknowledged: false },
  { id: 'al-3', time: '07:30 AM', title: 'Tire Pressure Sub-Optimal', description: 'Schedule check at next depot stop.', severity: 'warning', category: 'maintenance', vehicle: 'TRK-2041', acknowledged: false },
  { id: 'al-4', time: '06:45 AM', title: 'Approaching Hours of Service Limit', description: 'Driver has 45 minutes remaining before mandatory rest period.', severity: 'warning', category: 'driver', vehicle: 'DRV-74', acknowledged: false },
  { id: 'al-5', time: '05:10 AM', title: 'Demand Model Updated', description: 'Latest weather data incorporated into zone demand forecasting.', severity: 'info', category: 'demand', vehicle: 'SYS-01', acknowledged: false },
  { id: 'al-6', time: '04:30 AM', title: 'Delivery Density Increased', description: 'Zone E experiencing 15% higher than average parcel volume.', severity: 'info', category: 'demand', vehicle: 'ZONE-E', acknowledged: false },
]

export const routeTrend = [
  { day: 'Mon', actual: 48, planned: 45 },
  { day: 'Tue', actual: 55, planned: 51 },
  { day: 'Wed', actual: 50, planned: 49 },
  { day: 'Thu', actual: 62, planned: 58 },
  { day: 'Fri', actual: 67, planned: 64 },
  { day: 'Sat', actual: 61, planned: 60 },
]

export const demandTrend = [
  { day: 'Mon', actual: 2400, predicted: 2600 },
  { day: 'Tue', actual: 4300, predicted: 4100 },
  { day: 'Wed', actual: 3600, predicted: 3900 },
  { day: 'Thu', actual: 5200, predicted: 5400 },
  { day: 'Fri', actual: 6500, predicted: 7200 },
  { day: 'Sat', actual: 6100, predicted: 7600 },
]
