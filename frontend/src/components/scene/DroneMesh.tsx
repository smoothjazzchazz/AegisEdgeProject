import { useMemo } from 'react'
import type { TelemetryPoint } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'

interface Props {
  sample: TelemetryPoint
  color: string
  origin: Origin
  selected?: boolean
}

export function DroneMesh({ sample, color, origin, selected }: Props) {
  const pos = useMemo(
    () => toLocal(sample.latitude, sample.longitude, sample.altitude, origin),
    [sample, origin],
  )
  const yaw = ((90 - sample.heading) * Math.PI) / 180

  return (
    <group position={pos} rotation={[0, yaw, 0]}>
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
