export const DEMAND_DATA_CONTEXT_NOTE =
  'Sri Lanka demo scenario mapped from Olist-derived forecasting outputs; model has not been retrained using Sri Lankan demand data.'

export const SRI_LANKA_ZONES = [
  { id: 'LK_colombo_central', name: 'Colombo Central', latitude: 6.9271, longitude: 79.8612 },
  { id: 'LK_kandy_city', name: 'Kandy City', latitude: 7.2906, longitude: 80.6337 },
  { id: 'LK_galle_city', name: 'Galle City', latitude: 6.0329, longitude: 80.2168 },
  { id: 'LK_kurunegala', name: 'Kurunegala', latitude: 7.4863, longitude: 80.3647 },
  { id: 'LK_jaffna_city', name: 'Jaffna City', latitude: 9.6615, longitude: 80.0255 },
  { id: 'LK_negombo', name: 'Negombo', latitude: 7.2083, longitude: 79.8358 },
  { id: 'LK_gampaha', name: 'Gampaha', latitude: 7.0873, longitude: 80.0144 },
  { id: 'LK_matara', name: 'Matara', latitude: 5.9549, longitude: 80.555 },
  { id: 'LK_nugegoda', name: 'Nugegoda', latitude: 6.8649, longitude: 79.8997 },
  { id: 'LK_malabe', name: 'Malabe', latitude: 6.9061, longitude: 79.9696 },
] as const

const SOURCE_ZONE_TO_OPERATIONAL: Record<string, (typeof SRI_LANKA_ZONES)[number]> = {
  SP_sao_paulo: SRI_LANKA_ZONES[0],
  RJ_rio_de_janeiro: SRI_LANKA_ZONES[1],
  MG_belo_horizonte: SRI_LANKA_ZONES[2],
  DF_brasilia: SRI_LANKA_ZONES[3],
  PR_curitiba: SRI_LANKA_ZONES[4],
  SP_campinas: SRI_LANKA_ZONES[5],
  RS_porto_alegre: SRI_LANKA_ZONES[6],
  BA_salvador: SRI_LANKA_ZONES[7],
  SP_guarulhos: SRI_LANKA_ZONES[8],
  SP_sao_bernardo_do_campo: SRI_LANKA_ZONES[9],
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
