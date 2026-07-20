/** Client-side building proximity + trajectory (segment ∩ prism) analysis. */

export interface BuildingSolid {
  id: string
  footprint: number[][] // [lat, lon]
  height_m: number
}

export interface ClearanceResult {
  buildingId: string
  horizontal_m: number
  clearance_m: number
  penetrating: boolean
  overFootprint: boolean
  roof_m: number
}

export interface SamplePoint {
  latitude: number
  longitude: number
  altitude: number
}

interface Vec2 {
  x: number
  y: number
}

interface Vec3 {
  x: number
  y: number
  z: number
}

interface Origin {
  lat: number
  lon: number
}

function pointInRing(lat: number, lon: number, ring: number[][]): boolean {
  let inside = false
  const n = ring.length
  if (n < 3) return false
  let j = n - 1
  for (let i = 0; i < n; i++) {
    const yi = ring[i][0]
    const xi = ring[i][1]
    const yj = ring[j][0]
    const xj = ring[j][1]
    if (yi > lat !== yj > lat && lon < ((xj - xi) * (lat - yi)) / (yj - yi + 1e-15) + xi) {
      inside = !inside
    }
    j = i
  }
  return inside
}

function horizontalDistanceM(lat: number, lon: number, ring: number[][]): number {
  if (pointInRing(lat, lon, ring)) return 0
  const cosLat = Math.cos((lat * Math.PI) / 180)
  let best = Infinity
  for (let i = 0; i < ring.length - 1; i++) {
    const aLat = ring[i][0]
    const aLon = ring[i][1]
    const bLat = ring[i + 1][0]
    const bLon = ring[i + 1][1]
    const ax = (aLon - lon) * 111320 * cosLat
    const ay = (aLat - lat) * 111320
    const bx = (bLon - lon) * 111320 * cosLat
    const by = (bLat - lat) * 111320
    const abx = bx - ax
    const aby = by - ay
    const ab2 = abx * abx + aby * aby
    let dist: number
    if (ab2 < 1e-9) {
      dist = Math.hypot(ax, ay)
    } else {
      const t = Math.max(0, Math.min(1, (-ax * abx - ay * aby) / ab2))
      dist = Math.hypot(ax + t * abx, ay + t * aby)
    }
    if (dist < best) best = dist
  }
  return best === Infinity ? 0 : best
}

/** Distance to axis-aligned vertical prism (footprint × [0, roof]). */
export function clearanceToBuilding(
  lat: number,
  lon: number,
  altM: number,
  building: BuildingSolid,
): ClearanceResult {
  const roof = building.height_m
  const horiz = horizontalDistanceM(lat, lon, building.footprint)
  const over = horiz <= 0.5

  let clearance: number
  let penetrating = false

  if (over) {
    if (altM < 0) {
      clearance = -altM
      penetrating = true
    } else if (altM < roof) {
      clearance = altM - roof
      penetrating = true
    } else {
      clearance = altM - roof
    }
  } else if (altM >= 0 && altM < roof) {
    clearance = horiz
  } else if (altM >= roof) {
    clearance = Math.hypot(horiz, altM - roof)
  } else {
    clearance = Math.hypot(horiz, -altM)
    penetrating = altM < 0
  }

  return {
    buildingId: building.id,
    horizontal_m: horiz,
    clearance_m: clearance,
    penetrating,
    overFootprint: over,
    roof_m: roof,
  }
}

function toEnu(lat: number, lon: number, alt: number, origin: Origin): Vec3 {
  const cos = Math.cos((origin.lat * Math.PI) / 180)
  return {
    x: (lon - origin.lon) * 111320 * cos,
    y: (lat - origin.lat) * 111320,
    z: alt,
  }
}

function footprintToEnu(ring: number[][], origin: Origin): Vec2[] {
  const cos = Math.cos((origin.lat * Math.PI) / 180)
  const pts: Vec2[] = []
  for (const [lat, lon] of ring) {
    pts.push({
      x: (lon - origin.lon) * 111320 * cos,
      y: (lat - origin.lat) * 111320,
    })
  }
  if (
    pts.length > 1 &&
    Math.hypot(pts[0].x - pts[pts.length - 1].x, pts[0].y - pts[pts.length - 1].y) < 1e-6
  ) {
    pts.pop()
  }
  return pts
}

function pointInPoly2(x: number, y: number, poly: Vec2[]): boolean {
  let inside = false
  const n = poly.length
  if (n < 3) return false
  let j = n - 1
  for (let i = 0; i < n; i++) {
    const yi = poly[i].y
    const xi = poly[i].x
    const yj = poly[j].y
    const xj = poly[j].x
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi + 1e-15) + xi) {
      inside = !inside
    }
    j = i
  }
  return inside
}

function distPointSeg2(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): { d: number; t: number } {
  const abx = bx - ax
  const aby = by - ay
  const ab2 = abx * abx + aby * aby
  if (ab2 < 1e-12) {
    return { d: Math.hypot(px - ax, py - ay), t: 0 }
  }
  const t = Math.max(0, Math.min(1, ((px - ax) * abx + (py - ay) * aby) / ab2))
  return { d: Math.hypot(px - (ax + t * abx), py - (ay + t * aby)), t }
}

function distPointPoly2(x: number, y: number, poly: Vec2[]): number {
  if (pointInPoly2(x, y, poly)) return 0
  let best = Infinity
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i]
    const b = poly[(i + 1) % poly.length]
    best = Math.min(best, distPointSeg2(x, y, a.x, a.y, b.x, b.y).d)
  }
  return best
}

/** 2D segment–edge intersection parameter t on AB in [0,1], or null. */
function segSegIntersectT(
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number,
  dx: number,
  dy: number,
): number | null {
  const rX = bx - ax
  const rY = by - ay
  const sX = dx - cx
  const sY = dy - cy
  const den = rX * sY - rY * sX
  if (Math.abs(den) < 1e-12) return null
  const t = ((cx - ax) * sY - (cy - ay) * sX) / den
  const u = ((cx - ax) * rY - (cy - ay) * rX) / den
  if (t < -1e-9 || t > 1 + 1e-9 || u < -1e-9 || u > 1 + 1e-9) return null
  return Math.max(0, Math.min(1, t))
}

/** Parameter intervals of AB whose 2D projection lies inside the polygon. */
function insideIntervals2D(a: Vec2, b: Vec2, poly: Vec2[]): Array<[number, number]> {
  const ts = new Set<number>([0, 1])
  for (let i = 0; i < poly.length; i++) {
    const p = poly[i]
    const q = poly[(i + 1) % poly.length]
    const t = segSegIntersectT(a.x, a.y, b.x, b.y, p.x, p.y, q.x, q.y)
    if (t !== null) ts.add(t)
  }
  const sorted = [...ts].sort((u, v) => u - v)
  const intervals: Array<[number, number]> = []
  for (let i = 0; i < sorted.length - 1; i++) {
    const t0 = sorted[i]
    const t1 = sorted[i + 1]
    if (t1 - t0 < 1e-10) continue
    const tm = (t0 + t1) / 2
    const mx = a.x + (b.x - a.x) * tm
    const my = a.y + (b.y - a.y) * tm
    if (pointInPoly2(mx, my, poly)) {
      if (intervals.length && Math.abs(intervals[intervals.length - 1][1] - t0) < 1e-9) {
        intervals[intervals.length - 1][1] = t1
      } else {
        intervals.push([t0, t1])
      }
    }
  }
  return intervals
}

function rangesOverlap(a0: number, a1: number, b0: number, b1: number): boolean {
  const loA = Math.min(a0, a1)
  const hiA = Math.max(a0, a1)
  const loB = Math.min(b0, b1)
  const hiB = Math.max(b0, b1)
  return loA <= hiB + 1e-6 && loB <= hiA + 1e-6
}

/** True if 3D segment intersects the vertical prism (poly extruded [0, height]). */
export function segmentIntersectsPrism(
  a: Vec3,
  b: Vec3,
  poly: Vec2[],
  height: number,
): boolean {
  if (poly.length < 3) return false
  const H = Math.max(height, 0.1)

  // Endpoint inside solid
  for (const p of [a, b]) {
    if (p.z >= 0 && p.z <= H && pointInPoly2(p.x, p.y, poly)) return true
  }

  // Roof pierce: plane z = H
  if (Math.abs(b.z - a.z) > 1e-9) {
    const tH = (H - a.z) / (b.z - a.z)
    if (tH >= 0 && tH <= 1) {
      const x = a.x + (b.x - a.x) * tH
      const y = a.y + (b.y - a.y) * tH
      if (pointInPoly2(x, y, poly)) return true
    }
  }

  // Floor pierce z = 0
  if (Math.abs(b.z - a.z) > 1e-9) {
    const t0 = (0 - a.z) / (b.z - a.z)
    if (t0 >= 0 && t0 <= 1) {
      const x = a.x + (b.x - a.x) * t0
      const y = a.y + (b.y - a.y) * t0
      if (pointInPoly2(x, y, poly)) return true
    }
  }

  // Portions of the segment whose XY projection is inside the footprint
  const intervals = insideIntervals2D(a, b, poly)
  for (const [t0, t1] of intervals) {
    const z0 = a.z + (b.z - a.z) * t0
    const z1 = a.z + (b.z - a.z) * t1
    if (rangesOverlap(z0, z1, 0, H)) return true
  }

  return false
}

/** Min 2D distance from segment AB to polygon (0 if intersects / inside). */
function minDistSegPoly2(a: Vec2, b: Vec2, poly: Vec2[]): { dist: number; t: number } {
  if (pointInPoly2(a.x, a.y, poly) || pointInPoly2(b.x, b.y, poly)) {
    return { dist: 0, t: pointInPoly2(a.x, a.y, poly) ? 0 : 1 }
  }
  if (insideIntervals2D(a, b, poly).length) return { dist: 0, t: 0.5 }

  let best = Infinity
  let bestT = 0
  // Distance from each poly vertex to AB
  for (const p of poly) {
    const { d, t } = distPointSeg2(p.x, p.y, a.x, a.y, b.x, b.y)
    if (d < best) {
      best = d
      bestT = t
    }
  }
  // Distance from A/B to poly edges + closest approach between segments
  for (const end of [
    { x: a.x, y: a.y, t: 0 },
    { x: b.x, y: b.y, t: 1 },
  ]) {
    const d = distPointPoly2(end.x, end.y, poly)
    if (d < best) {
      best = d
      bestT = end.t
    }
  }
  for (let i = 0; i < poly.length; i++) {
    const p = poly[i]
    const q = poly[(i + 1) % poly.length]
    // Closest between two segments: check intersection → 0, else endpoints already covered;
    // also project AB onto edge and edge onto AB via endpoint projections (done) —
    // add mid critical: solve for mutual closest
    const tHit = segSegIntersectT(a.x, a.y, b.x, b.y, p.x, p.y, q.x, q.y)
    if (tHit !== null) return { dist: 0, t: tHit }
  }
  return { dist: best, t: bestT }
}

/**
 * Clearance of a 3D trajectory segment to a building prism.
 * Uses continuous segment∩prism for collisions; critical-point clearance otherwise.
 */
export function segmentClearanceToBuilding(
  a: SamplePoint,
  b: SamplePoint,
  building: BuildingSolid,
): ClearanceResult {
  const origin: Origin = {
    lat: (a.latitude + b.latitude) / 2,
    lon: (a.longitude + b.longitude) / 2,
  }
  const A = toEnu(a.latitude, a.longitude, a.altitude, origin)
  const B = toEnu(b.latitude, b.longitude, b.altitude, origin)
  const poly = footprintToEnu(building.footprint, origin)
  const H = building.height_m

  if (segmentIntersectsPrism(A, B, poly, H)) {
    return {
      buildingId: building.id,
      horizontal_m: 0,
      clearance_m: 0,
      penetrating: true,
      overFootprint: true,
      roof_m: H,
    }
  }

  // Critical parameters along the segment for min clearance
  const ts = new Set<number>([0, 1])
  if (Math.abs(B.z - A.z) > 1e-9) {
    const tH = (H - A.z) / (B.z - A.z)
    if (tH > 0 && tH < 1) ts.add(tH)
    const tG = (0 - A.z) / (B.z - A.z)
    if (tG > 0 && tG < 1) ts.add(tG)
  }
  const { t: tClosest } = minDistSegPoly2(A, B, poly)
  ts.add(tClosest)
  // Edge-entry parameters (footprint crossings)
  for (let i = 0; i < poly.length; i++) {
    const p = poly[i]
    const q = poly[(i + 1) % poly.length]
    const t = segSegIntersectT(A.x, A.y, B.x, B.y, p.x, p.y, q.x, q.y)
    if (t !== null) ts.add(t)
  }

  let best: ClearanceResult | null = null
  for (const t of ts) {
    const lat = a.latitude + (b.latitude - a.latitude) * t
    const lon = a.longitude + (b.longitude - a.longitude) * t
    const alt = a.altitude + (b.altitude - a.altitude) * t
    const c = clearanceToBuilding(lat, lon, alt, building)
    if (!best || c.clearance_m < best.clearance_m) best = c
  }

  return (
    best ?? {
      buildingId: building.id,
      horizontal_m: 0,
      clearance_m: Infinity,
      penetrating: false,
      overFootprint: false,
      roof_m: H,
    }
  )
}

export function nearestBuildingClearance(
  lat: number,
  lon: number,
  altM: number,
  buildings: BuildingSolid[],
): ClearanceResult | null {
  if (!buildings.length) return null
  let best: ClearanceResult | null = null
  for (const b of buildings) {
    const c = clearanceToBuilding(lat, lon, altM, b)
    if (!best || c.clearance_m < best.clearance_m) best = c
  }
  return best
}

/** Buildings within threshold (or penetrating) of a sample. */
export function buildingsAtRisk(
  lat: number,
  lon: number,
  altM: number,
  buildings: BuildingSolid[],
  thresholdM: number,
): {
  collisionIds: Set<string>
  riskIds: Set<string>
  nearest: ClearanceResult | null
} {
  const collisionIds = new Set<string>()
  const riskIds = new Set<string>()
  let nearest: ClearanceResult | null = null
  for (const b of buildings) {
    const c = clearanceToBuilding(lat, lon, altM, b)
    if (!nearest || c.clearance_m < nearest.clearance_m) nearest = c
    if (c.penetrating) collisionIds.add(b.id)
    else if (c.clearance_m < thresholdM) riskIds.add(b.id)
  }
  return { collisionIds, riskIds, nearest }
}

/**
 * Trajectory analysis: each consecutive sample pair is a 3D segment tested
 * against every building prism (intersection → collision; min clearance → risk).
 */
export function buildingsClassifiedDuringFlight(
  samples: SamplePoint[],
  buildings: BuildingSolid[],
  thresholdM: number,
): { collisionIds: Set<string>; riskIds: Set<string> } {
  const collisionIds = new Set<string>()
  const riskIds = new Set<string>()
  if (!samples.length || !buildings.length) return { collisionIds, riskIds }

  // Trajectory AABB (+ padding) to skip far buildings quickly
  let minLat = Infinity
  let maxLat = -Infinity
  let minLon = Infinity
  let maxLon = -Infinity
  for (const p of samples) {
    minLat = Math.min(minLat, p.latitude)
    maxLat = Math.max(maxLat, p.latitude)
    minLon = Math.min(minLon, p.longitude)
    maxLon = Math.max(maxLon, p.longitude)
  }
  const padDeg = (thresholdM + 50) / 111320

  const candidates = buildings.filter((b) => {
    if (b.height_m < 0) return false
    // Quick reject if footprint AABB is far from trajectory AABB
    let bMinLat = Infinity
    let bMaxLat = -Infinity
    let bMinLon = Infinity
    let bMaxLon = -Infinity
    for (const [lat, lon] of b.footprint) {
      bMinLat = Math.min(bMinLat, lat)
      bMaxLat = Math.max(bMaxLat, lat)
      bMinLon = Math.min(bMinLon, lon)
      bMaxLon = Math.max(bMaxLon, lon)
    }
    return !(
      bMaxLat < minLat - padDeg ||
      bMinLat > maxLat + padDeg ||
      bMaxLon < minLon - padDeg ||
      bMinLon > maxLon + padDeg
    )
  })

  if (samples.length === 1) {
    const p = samples[0]
    for (const b of candidates) {
      const c = clearanceToBuilding(p.latitude, p.longitude, p.altitude, b)
      if (c.penetrating) collisionIds.add(b.id)
      else if (c.clearance_m < thresholdM) riskIds.add(b.id)
    }
    for (const id of collisionIds) riskIds.delete(id)
    return { collisionIds, riskIds }
  }

  for (const b of candidates) {
    // Skip buildings whose roof is far below all flight alts and laterally distant — still check
    let everPenetrating = false
    let minClearance = Infinity

    for (let i = 0; i < samples.length - 1; i++) {
      const c = segmentClearanceToBuilding(samples[i], samples[i + 1], b)
      if (c.penetrating) {
        everPenetrating = true
        break
      }
      if (c.clearance_m < minClearance) minClearance = c.clearance_m
    }

    if (everPenetrating) collisionIds.add(b.id)
    else if (minClearance < thresholdM) riskIds.add(b.id)
  }

  for (const id of collisionIds) riskIds.delete(id)
  return { collisionIds, riskIds }
}

/** Closest point on footprint ring to a lat/lon (for clearance line endpoint). */
export function closestFootprintPoint(
  lat: number,
  lon: number,
  ring: number[][],
): { lat: number; lon: number } {
  if (!ring.length) return { lat, lon }
  const cosLat = Math.cos((lat * Math.PI) / 180)
  let bestD = Infinity
  let best = { lat: ring[0][0], lon: ring[0][1] }
  for (let i = 0; i < ring.length - 1; i++) {
    const aLat = ring[i][0]
    const aLon = ring[i][1]
    const bLat = ring[i + 1][0]
    const bLon = ring[i + 1][1]
    const ax = (aLon - lon) * 111320 * cosLat
    const ay = (aLat - lat) * 111320
    const bx = (bLon - lon) * 111320 * cosLat
    const by = (bLat - lat) * 111320
    const abx = bx - ax
    const aby = by - ay
    const ab2 = abx * abx + aby * aby
    const t = ab2 < 1e-9 ? 0 : Math.max(0, Math.min(1, (-ax * abx - ay * aby) / ab2))
    const cLat = aLat + (bLat - aLat) * t
    const cLon = aLon + (bLon - aLon) * t
    const d = Math.hypot(
      (cLon - lon) * 111320 * cosLat,
      (cLat - lat) * 111320,
    )
    if (d < bestD) {
      bestD = d
      best = { lat: cLat, lon: cLon }
    }
  }
  return best
}

export function buildingsHitDuringFlight(
  samples: SamplePoint[],
  buildings: BuildingSolid[],
  thresholdM: number,
): Set<string> {
  const { collisionIds, riskIds } = buildingsClassifiedDuringFlight(
    samples,
    buildings,
    thresholdM,
  )
  return new Set<string>([...collisionIds, ...riskIds])
}
