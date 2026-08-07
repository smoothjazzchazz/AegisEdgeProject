import { memo, useMemo } from 'react'
import * as THREE from 'three'
import type { OsmBuilding } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'

interface Props {
  building: OsmBuilding
  origin: Origin
  /** Live proximity at scrubber time */
  hot?: boolean
  /** Came within threshold at any point during the flight */
  hit?: boolean
}

/**
 * Build a vertical prism from a lat/lon ring.
 * Avoids Shape/Extrude winding surprises by constructing the mesh explicitly.
 */
function buildPrismGeometry(
  footprint: number[][],
  heightM: number,
  origin: Origin,
): THREE.BufferGeometry | null {
  const ring = footprint.map(([lat, lon]) => {
    const [x, , z] = toLocal(lat, lon, 0, origin)
    return new THREE.Vector2(x, z) // (east, threeZ=-north)
  })

  // Drop closing duplicate
  if (ring.length > 1 && ring[0].distanceTo(ring[ring.length - 1]) < 1e-8) {
    ring.pop()
  }
  // Simplify very dense OSM ways for stable mesh + perf
  const simplified =
    ring.length > 48
      ? ring.filter((_, i) => i % Math.ceil(ring.length / 40) === 0 || i === ring.length - 1)
      : ring

  if (simplified.length < 3) return null

  const h = Math.max(heightM / 100, 0.04) // scene units (same as drone alt scale)
  const n = simplified.length
  const positions: number[] = []
  const indices: number[] = []

  // Bottom ring y=0, top ring y=h
  for (const p of simplified) {
    positions.push(p.x, 0, p.y)
  }
  for (const p of simplified) {
    positions.push(p.x, h, p.y)
  }

  // Side walls (two triangles per edge)
  for (let i = 0; i < n; i++) {
    const j = (i + 1) % n
    const b0 = i
    const b1 = j
    const t0 = i + n
    const t1 = j + n
    indices.push(b0, b1, t1, b0, t1, t0)
  }

  // Roof fan (and optional floor) — ensure outward-ish by using ear from vertex 0
  for (let i = 1; i < n - 1; i++) {
    indices.push(n + 0, n + i, n + i + 1) // roof
    indices.push(0, i + 1, i) // floor (reversed)
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3))
  geo.setIndex(indices)
  geo.computeVertexNormals()
  return geo
}

export const BuildingMesh = memo(function BuildingMesh({
  building,
  origin,
  hot,
  hit,
}: Props) {
  const geometry = useMemo(
    () => buildPrismGeometry(building.footprint, building.height_m, origin),
    [building, origin],
  )

  const edges = useMemo(() => {
    if (!geometry) return null
    return new THREE.EdgesGeometry(geometry, 30)
  }, [geometry])

  if (!geometry) return null

  // Live near / collision (red) wins over flight-risk (amber)
  const color = hot ? '#c45c5c' : hit ? '#c4a35a' : '#4a5d6e'
  const emissive = hot ? '#ff6b4a' : hit ? '#c4a35a' : '#243040'
  const emissiveIntensity = hot ? 0.55 : hit ? 0.35 : 0.12
  const opacity = hot ? 0.9 : hit ? 0.8 : 0.65
  const edgeColor = hot ? '#ffb0a0' : hit ? '#e8d090' : '#8aa0b4'

  return (
    <group>
      <mesh geometry={geometry}>
        <meshStandardMaterial
          color={color}
          emissive={emissive}
          emissiveIntensity={emissiveIntensity}
          transparent
          opacity={opacity}
          side={THREE.DoubleSide}
          depthWrite
          metalness={0.1}
          roughness={0.85}
        />
      </mesh>
      {edges && (
        <lineSegments geometry={edges}>
          <lineBasicMaterial
            color={edgeColor}
            transparent
            opacity={hot || hit ? 1 : 0.55}
          />
        </lineSegments>
      )}
    </group>
  )
})
