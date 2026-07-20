import { useMemo } from 'react'
import type { RiskZone } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'
import * as THREE from 'three'

interface Props {
  zone: RiskZone
  origin: Origin
}

export function RiskZoneMesh({ zone, origin }: Props) {
  const { center, size } = useMemo(() => {
    const locals = zone.vertices.map((v) => toLocal(v[0], v[1], v[2], origin))
    const xs = locals.map((p) => p[0])
    const ys = locals.map((p) => p[1])
    const zs = locals.map((p) => p[2])
    const minX = Math.min(...xs)
    const maxX = Math.max(...xs)
    const minY = Math.min(...ys)
    const maxY = Math.max(...ys)
    const minZ = Math.min(...zs)
    const maxZ = Math.max(...zs)
    return {
      center: new THREE.Vector3(
        (minX + maxX) / 2,
        (minY + maxY) / 2,
        (minZ + maxZ) / 2,
      ),
      size: [Math.max(maxX - minX, 0.01), Math.max(maxY - minY, 0.01), Math.max(maxZ - minZ, 0.01)] as [
        number,
        number,
        number,
      ],
    }
  }, [zone, origin])

  const opacity = Math.min(0.15 + zone.density / 80, 0.4)

  return (
    <mesh position={center}>
      <boxGeometry args={size} />
      <meshStandardMaterial
        color="#c45c5c"
        transparent
        opacity={opacity}
        depthWrite={false}
      />
    </mesh>
  )
}
