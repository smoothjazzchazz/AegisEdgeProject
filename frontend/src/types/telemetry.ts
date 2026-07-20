export interface TelemetryPoint {
  aircraft_id: string
  timestamp: string
  latitude: number
  longitude: number
  altitude: number
  heading: number
}

export interface DroneSummary {
  aircraft_id: string
  point_count: number
  t_min: string
  t_max: string
  alt_min: number
  alt_max: number
  alt_avg: number
}

export interface FleetResponse {
  drones: DroneSummary[]
  t_min: string | null
  t_max: string | null
  total_points: number
}

export interface TrajectoriesResponse {
  points: TelemetryPoint[]
  sampled: boolean
  total_before_sample: number
}

export interface CollisionSample {
  timestamp: string
  distance_m: number
  risk: number
}

export interface CollisionResponse {
  samples: CollisionSample[]
  min_distance_m: number
  avg_distance_m: number
  max_risk: number
  time_at_risk_pct: number
}

export interface RiskZone {
  vertices: number[][]
  density: number
  avg_altitude: number
}

export interface PathPoint {
  latitude: number
  longitude: number
  altitude: number
}

export interface CorridorResponse {
  direct_path: PathPoint[]
  optimized_path: PathPoint[]
  zones: RiskZone[]
  direct_length_km: number
  optimized_length_km: number
  path_difference_pct: number
  avg_altitude: number
  risk_zones_avoided: number
  buildings_avoided?: number
  buildings_loaded?: number
}

export interface UploadResponse {
  success: boolean
  message: string
  total_points: number
  drones_added: string[]
  t_min: string | null
  t_max: string | null
}

export type DrawerMode = 'collision' | 'corridor' | 'data' | 'buildings' | null

export interface OsmBuilding {
  id: string
  footprint: number[][] // [lat, lon]
  height_m: number
  name?: string | null
  levels?: number | null
}

export interface BuildingsResponse {
  buildings: OsmBuilding[]
  count: number
  bbox: number[] | null
  source: string
}

export interface BuildingRiskSample {
  timestamp: string
  clearance_m: number
  horizontal_m: number
  risk: number
  penetrating: boolean
  building_id: string
  over_footprint: boolean
}

export interface BuildingRiskResponse {
  aircraft_id: string
  samples: BuildingRiskSample[]
  min_clearance_m: number
  time_at_risk_pct: number
  penetration_count: number
  nearest_building_id: string | null
  threshold_m: number
  buildings_checked: number
  trajectory_collisions?: number
  trajectory_risk_buildings?: number
}

export const DRONE_COLORS = [
  '#5b8fa8',
  '#d97757',
  '#4a9b6e',
  '#c4a35a',
  '#8b6bb5',
  '#3d9b9b',
  '#c4784a',
  '#6b8f9e',
]
