import { Line } from '@react-three/drei'
import { useMemo } from 'react'
import type { PathPoint } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'

interface Props {
  direct: PathPoint[]
  optimized: PathPoint[]
  origin: Origin
}

export function CorridorPath({ direct, optimized, origin }: Props) {
  const directPts = useMemo(
    () => direct.map((p) => toLocal(p.latitude, p.longitude, p.altitude, origin)),
    [direct, origin],
  )
  const optPts = useMemo(
    () => optimized.map((p) => toLocal(p.latitude, p.longitude, p.altitude, origin)),
    [optimized, origin],
  )

  return (
    <group>
      {directPts.length >= 2 && (
        <Line points={directPts} color="#c45c5c" lineWidth={2} dashed dashSize={0.08} gapSize={0.05} />
      )}
      {optPts.length >= 2 && (
        <Line points={optPts} color="#4a9b6e" lineWidth={3.5} />
      )}
      {optPts.length > 0 && (
        <>
          <mesh position={optPts[0]}>
            <sphereGeometry args={[0.06, 12, 12]} />
            <meshStandardMaterial color="#4a9b6e" emissive="#4a9b6e" emissiveIntensity={0.4} />
          </mesh>
          <mesh position={optPts[optPts.length - 1]}>
            <sphereGeometry args={[0.06, 12, 12]} />
            <meshStandardMaterial color="#c45c5c" emissive="#c45c5c" emissiveIntensity={0.4} />
          </mesh>
        </>
      )}
    </group>
  )
}
