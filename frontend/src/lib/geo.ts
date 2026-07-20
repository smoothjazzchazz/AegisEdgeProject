/** WGS84 helpers → local ENU-ish meters for Three.js */

export interface Origin {
  lat: number
  lon: number
}

export function computeOrigin(
  points: { latitude: number; longitude: number }[],
): Origin {
  if (!points.length) return { lat: 40.7829, lon: -73.9654 }
  const lat = points.reduce((s, p) => s + p.latitude, 0) / points.length
  const lon = points.reduce((s, p) => s + p.longitude, 0) / points.length
  return { lat, lon }
}

/** Returns [x east km, y north km, z alt m] — z kept in meters for readable altitude scale */
export function toLocal(
  lat: number,
  lon: number,
  alt: number,
  origin: Origin,
): [number, number, number] {
  const x = (lon - origin.lon) * 111.32 * Math.cos((origin.lat * Math.PI) / 180)
  const y = (lat - origin.lat) * 111.32
  // Scale altitude to km-ish so scene aspect is reasonable (alt/1000 → km),
  // but we use alt/100 so vertical is exaggerated ~10x for ATC readability
  const z = alt / 100
  return [x, z, -y] // Three.js: y up, so map north to -z
}

export function haversineApproxM(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
  alt1: number,
  alt2: number,
): number {
  const dx = (lon2 - lon1) * 111320 * Math.cos((lat1 * Math.PI) / 180)
  const dy = (lat2 - lat1) * 111320
  const dz = alt2 - alt1
  return Math.sqrt(dx * dx + dy * dy + dz * dz)
}
