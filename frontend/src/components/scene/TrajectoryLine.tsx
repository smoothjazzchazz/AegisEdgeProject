import { Line } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { useMemo, useRef, useState } from 'react'
import type { TelemetryPoint } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'
import { indexAtOrBefore } from '@/lib/telemetry'
import { visualTRef } from '@/lib/replayClock'

interface Props {
  points: TelemetryPoint[]
  color: string
  origin: Origin
}

export function TrajectoryLine({ points, color, origin }: Props) {
  const full = useMemo(
    () => points.map((p) => toLocal(p.latitude, p.longitude, p.altitude, origin)),
    [points, origin],
  )

  const endRef = useRef(0)
  const [playedEnd, setPlayedEnd] = useState(() =>
    Math.max(0, indexAtOrBefore(points, visualTRef.current) + 1),
  )

  useFrame(() => {
    const next = Math.max(0, indexAtOrBefore(points, visualTRef.current) + 1)
    if (next !== endRef.current) {
      endRef.current = next
      setPlayedEnd(next)
    }
  })

  const played = useMemo(() => full.slice(0, playedEnd), [full, playedEnd])

  if (full.length < 2) return null

  return (
    <group>
      <Line points={full} color={color} lineWidth={1} transparent opacity={0.25} />
      {played.length >= 2 && (
        <Line points={played} color={color} lineWidth={2.5} transparent opacity={0.95} />
      )}
    </group>
  )
}
