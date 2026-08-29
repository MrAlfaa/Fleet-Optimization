export const DEMAND_DATA_CONTEXT_NOTE =
  'Colombo operational demand forecast with live-order comparison and fleet capacity planning.'

export const SRI_LANKA_ZONES = [
  { id: 'LK_colombo_central', name: 'Colombo Central', latitude: 6.9271, longitude: 79.8612 },
  { id: 'LK_nugegoda', name: 'Nugegoda', latitude: 6.8649, longitude: 79.8997 },
  { id: 'LK_malabe', name: 'Malabe', latitude: 6.9061, longitude: 79.9696 },
  { id: 'LK_dehiwala', name: 'Dehiwala', latitude: 6.8511, longitude: 79.8659 },
  { id: 'LK_mount_lavinia', name: 'Mount Lavinia', latitude: 6.8389, longitude: 79.8638 },
  { id: 'LK_rajagiriya', name: 'Rajagiriya', latitude: 6.9097, longitude: 79.8943 },
  { id: 'LK_battaramulla', name: 'Battaramulla', latitude: 6.9022, longitude: 79.9197 },
  { id: 'LK_kaduwela', name: 'Kaduwela', latitude: 6.9319, longitude: 79.9842 },
  { id: 'LK_moratuwa', name: 'Moratuwa', latitude: 6.773, longitude: 79.8816 },
  { id: 'LK_kotte', name: 'Sri Jayawardenepura Kotte', latitude: 6.8905, longitude: 79.9015 },
  { id: 'LK_wellawatte', name: 'Wellawatte', latitude: 6.8747, longitude: 79.8605 },
  { id: 'LK_kollupitiya', name: 'Kollupitiya', latitude: 6.9105, longitude: 79.8503 },
  { id: 'LK_borella', name: 'Borella', latitude: 6.9147, longitude: 79.8777 },
  { id: 'LK_wattala', name: 'Wattala', latitude: 6.9897, longitude: 79.8927 },
  { id: 'LK_piliyandala', name: 'Piliyandala', latitude: 6.8018, longitude: 79.9227 },
] as const

const SOURCE_ZONE_TO_OPERATIONAL: Record<string, (typeof SRI_LANKA_ZONES)[number]> = {
  SP_sao_paulo: SRI_LANKA_ZONES[0],
  SP_guarulhos: SRI_LANKA_ZONES[1],
  SP_sao_bernardo_do_campo: SRI_LANKA_ZONES[2],
}

export function zoneDisplayName(value: string) {
  return SOURCE_ZONE_TO_OPERATIONAL[value]?.name ?? SRI_LANKA_ZONES.find((zone) => zone.id === value)?.name ?? value
}

export function localizeZoneText(value: string) {
  return Object.entries(SOURCE_ZONE_TO_OPERATIONAL).reduce(
    (text, [sourceId, zone]) => text.replaceAll(sourceId, zone.name),
    value,
  )
}

export const VEHICLE_CATEGORIES = [
  { value: 'electric_van', label: 'Electric Van' },
  { value: 'electric_truck', label: 'Electric Truck' },
  { value: 'electric_car', label: 'Electric Car' },
  { value: 'electric_bus', label: 'Electric Bus' },
  { value: 'other', label: 'Other' },
] as const

export function vehicleCategoryLabel(value: string) {
  return VEHICLE_CATEGORIES.find((category) => category.value === value)?.label ?? value.replaceAll('_', ' ')
}
