import type {
  BuildingRiskResponse,
  BuildingsResponse,
  CollisionResponse,
  CorridorResponse,
  FleetResponse,
  RiskZone,
  TrajectoriesResponse,
  UploadResponse,
} from '@/types/telemetry'

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text()
    let detail = text
    try {
      const parsed = JSON.parse(text)
      detail = parsed.detail ?? text
    } catch {
      /* keep text */
    }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => fetch('/api/health').then((r) => json<{ status: string }>(r)),

  fleet: () => fetch('/api/fleet').then((r) => json<FleetResponse>(r)),

  trajectories: (ids?: string[], t0?: string, t1?: string) => {
    const params = new URLSearchParams()
    if (ids?.length) params.set('ids', ids.join(','))
    if (t0) params.set('t0', t0)
    if (t1) params.set('t1', t1)
    const q = params.toString()
    return fetch(`/api/trajectories${q ? `?${q}` : ''}`).then((r) =>
      json<TrajectoriesResponse>(r),
    )
  },

  upload: async (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return fetch('/api/upload', { method: 'POST', body: form }).then((r) =>
      json<UploadResponse>(r),
    )
  },

  reloadDemo: () =>
    fetch('/api/demo/reload', { method: 'POST' }).then((r) =>
      json<UploadResponse>(r),
    ),

  collision: (drone_a: string, drone_b: string, threshold_m: number) =>
    fetch('/api/analysis/collision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ drone_a, drone_b, threshold_m }),
    }).then((r) => json<CollisionResponse>(r)),

  congestion: (drone_ids?: string[]) =>
    fetch('/api/analysis/congestion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ drone_ids }),
    }).then((r) => json<{ zones: RiskZone[] }>(r)),

  corridor: (body: {
    start: { lat: number; lon: number }
    end: { lat: number; lon: number }
    altitude_m: number
    drone_ids?: string[]
  }) =>
    fetch('/api/analysis/corridor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then((r) => json<CorridorResponse>(r)),

  buildings: () =>
    fetch('/api/buildings').then((r) => json<BuildingsResponse>(r)),

  loadBuildings: (pad_deg = 0.004) =>
    fetch('/api/buildings/load', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pad_deg }),
    }).then((r) => json<BuildingsResponse>(r)),

  clearBuildings: () =>
    fetch('/api/buildings', { method: 'DELETE' }).then((r) =>
      json<BuildingsResponse>(r),
    ),

  buildingRisk: (aircraft_id: string, threshold_m: number) =>
    fetch('/api/buildings/risk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ aircraft_id, threshold_m }),
    }).then((r) => json<BuildingRiskResponse>(r)),
}
