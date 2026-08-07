import type { TelemetryPoint } from '@/types/telemetry'

const timesCache = new WeakMap<TelemetryPoint[], number[]>()

function getTimes(series: TelemetryPoint[]): number[] {
  let times = timesCache.get(series)
  if (!times) {
    times = series.map((p) => new Date(p.timestamp).getTime())
    timesCache.set(series, times)
  }
  return times
}

export function pointsByDrone(
  points: TelemetryPoint[],
  ids: string[],
): Map<string, TelemetryPoint[]> {
  const map = new Map<string, TelemetryPoint[]>()
  for (const id of ids) map.set(id, [])
  for (const p of points) {
    if (!map.has(p.aircraft_id)) continue
    map.get(p.aircraft_id)!.push(p)
  }
  for (const [, arr] of map) {
    arr.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
  }
  return map
}

/** Last index with timestamp <= tMs, or -1 if none. */
export function indexAtOrBefore(series: TelemetryPoint[], tMs: number): number {
  if (!series.length) return -1
  const times = getTimes(series)
  if (tMs < times[0]) return -1
  if (tMs >= times[times.length - 1]) return times.length - 1
  let lo = 0
  let hi = times.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (times[mid] <= tMs) lo = mid
    else hi = mid
  }
  return times[hi] <= tMs ? hi : lo
}

/** Interpolate position for aircraft at time t (ms). */
export function sampleAt(
  series: TelemetryPoint[],
  tMs: number,
): TelemetryPoint | null {
  if (!series.length) return null
  const times = getTimes(series)
  if (tMs <= times[0]) return series[0]
  if (tMs >= times[times.length - 1]) return series[series.length - 1]

  let lo = 0
  let hi = series.length - 1
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1
    if (times[mid] <= tMs) lo = mid
    else hi = mid
  }

  const a = series[lo]
  const b = series[hi]
  const ta = times[lo]
  const tb = times[hi]
  const u = tb === ta ? 0 : (tMs - ta) / (tb - ta)

  return {
    aircraft_id: a.aircraft_id,
    timestamp: new Date(tMs).toISOString(),
    latitude: a.latitude + (b.latitude - a.latitude) * u,
    longitude: a.longitude + (b.longitude - a.longitude) * u,
    altitude: a.altitude + (b.altitude - a.altitude) * u,
    heading: a.heading + shortestAngleDelta(a.heading, b.heading) * u,
  }
}

function shortestAngleDelta(a: number, b: number): number {
  let d = b - a
  while (d > 180) d -= 360
  while (d < -180) d += 360
  return d
}

export function seriesUpTo(series: TelemetryPoint[], tMs: number): TelemetryPoint[] {
  const idx = indexAtOrBefore(series, tMs)
  if (idx < 0) return []
  return series.slice(0, idx + 1)
}
