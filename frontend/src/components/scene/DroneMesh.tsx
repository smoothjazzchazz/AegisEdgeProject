import { useFrame } from '@react-three/fiber'
import { useRef } from 'react'
import type { Group } from 'three'
import type { TelemetryPoint } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'
import { sampleAt } from '@/lib/telemetry'
import { visualTRef } from '@/lib/replayClock'

interface Props {
  series: TelemetryPoint[]
  color: string
  origin: Origin
  selected?: boolean
}

/** Pose updates from visualTRef inside the R3F frame loop — no React re-render per tick. */
export function DroneMesh({ series, color, origin, selected }: Props) {
  const ref = useRef<Group>(null)

  useFrame(() => {
    const group = ref.current
    if (!group || !series.length) return
    const sample = sampleAt(series, visualTRef.current)
    if (!sample) return
    const [x, y, z] = toLocal(sample.latitude, sample.longitude, sample.altitude, origin)
    group.position.set(x, y, z)
    group.rotation.y = ((90 - sample.heading) * Math.PI) / 180
  })

  return (
    <group ref={ref}>
      <mesh>
        <coneGeometry args={[0.04, 0.12, 4]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={selected ? 0.45 : 0.2}
        />
      </mesh>
      <mesh position={[0, 0.02, 0]} rotation={[0, 0, Math.PI / 2]}>
        <boxGeometry args={[0.02, 0.14, 0.02]} />
        <meshStandardMaterial color={color} transparent opacity={0.7} />
      </mesh>
    </group>
  )
}
