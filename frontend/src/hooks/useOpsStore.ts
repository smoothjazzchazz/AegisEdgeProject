import { create } from 'zustand'
import type {
  BuildingRiskResponse,
  CollisionResponse,
  CorridorResponse,
  DroneSummary,
  DrawerMode,
  OsmBuilding,
  RiskZone,
  TelemetryPoint,
} from '@/types/telemetry'

interface OpsState {
  drones: DroneSummary[]
  selectedIds: string[]
  points: TelemetryPoint[]
  tMin: number
  tMax: number
  t: number
  playing: boolean
  speed: number
  drawer: DrawerMode
  chartsOpen: boolean
  collision: CollisionResponse | null
  corridor: CorridorResponse | null
  riskZones: RiskZone[]
  buildings: OsmBuilding[]
  buildingsVisible: boolean
  buildingRisk: BuildingRiskResponse | null
  /** User-set clearance risk threshold (meters) for amber highlights */
  buildingThresholdM: number
  hotBuildingIds: Set<string>
  followSelected: boolean
  loading: boolean
  error: string | null
  wsConnected: boolean

  setFleet: (drones: DroneSummary[], tMin: string | null, tMax: string | null) => void
  setSelectedIds: (ids: string[]) => void
  toggleSelected: (id: string) => void
  setPoints: (points: TelemetryPoint[]) => void
  setT: (t: number) => void
  setPlaying: (playing: boolean) => void
  setSpeed: (speed: number) => void
  setDrawer: (drawer: DrawerMode) => void
  setChartsOpen: (open: boolean) => void
  setCollision: (c: CollisionResponse | null) => void
  setCorridor: (c: CorridorResponse | null) => void
  setRiskZones: (z: RiskZone[]) => void
  setBuildings: (b: OsmBuilding[]) => void
  setBuildingsVisible: (v: boolean) => void
  setBuildingRisk: (r: BuildingRiskResponse | null) => void
  setBuildingThresholdM: (m: number) => void
  setHotBuildingIds: (ids: Set<string>) => void
  setFollowSelected: (v: boolean) => void
  setLoading: (v: boolean) => void
  setError: (e: string | null) => void
  setWsConnected: (v: boolean) => void
}

export const useOpsStore = create<OpsState>((set, get) => ({
  drones: [],
  selectedIds: [],
  points: [],
  tMin: 0,
  tMax: 1,
  t: 0,
  playing: false,
  speed: 1,
  drawer: null,
  chartsOpen: true,
  collision: null,
  corridor: null,
  riskZones: [],
  buildings: [],
  buildingsVisible: true,
  buildingRisk: null,
  buildingThresholdM: 30,
  hotBuildingIds: new Set(),
  followSelected: false,
  loading: false,
  error: null,
  wsConnected: false,

  setFleet: (drones, tMin, tMax) => {
    const min = tMin ? new Date(tMin).getTime() : 0
    const max = tMax ? new Date(tMax).getTime() : 1
    const selected = get().selectedIds.filter((id) =>
      drones.some((d) => d.aircraft_id === id),
    )
    set({
      drones,
      tMin: min,
      tMax: max,
      t: get().t >= min && get().t <= max ? get().t : min,
      selectedIds: selected.length ? selected : drones.map((d) => d.aircraft_id),
    })
  },

  setSelectedIds: (ids) => set({ selectedIds: ids }),
  toggleSelected: (id) => {
    const cur = get().selectedIds
    set({
      selectedIds: cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id],
    })
  },
  setPoints: (points) => set({ points }),
  setT: (t) => set({ t }),
  setPlaying: (playing) => set({ playing }),
  setSpeed: (speed) => set({ speed }),
  setDrawer: (drawer) => set({ drawer }),
  setChartsOpen: (chartsOpen) => set({ chartsOpen }),
  setCollision: (collision) => set({ collision }),
  setCorridor: (corridor) => set({ corridor }),
  setRiskZones: (riskZones) => set({ riskZones }),
  setBuildings: (buildings) => set({ buildings }),
  setBuildingsVisible: (buildingsVisible) => set({ buildingsVisible }),
  setBuildingRisk: (buildingRisk) => {
    set({ buildingRisk })
  },
  setBuildingThresholdM: (buildingThresholdM) => set({ buildingThresholdM }),
  setHotBuildingIds: (hotBuildingIds) => set({ hotBuildingIds }),
  setFollowSelected: (followSelected) => set({ followSelected }),
  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),
  setWsConnected: (wsConnected) => set({ wsConnected }),
}))
