import { Line } from '@react-three/drei'
import { useMemo } from 'react'
import type { TelemetryPoint } from '@/types/telemetry'
import { toLocal, type Origin } from '@/lib/geo'
import { seriesUpTo } from '@/lib/telemetry'

interface Props {
  points: TelemetryPoint[]
  color: string
  tMs: number
  origin: Origin
}

export function TrajectoryLine({ points, color, tMs, origin }: Props) {
  const { full, played } = useMemo(() => {
    const fullPts = points.map((p) => toLocal(p.latitude, p.longitude, p.altitude, origin))
    const playedSeries = seriesUpTo(points, tMs)
    const playedPts = playedSeries.map((p) =>
      toLocal(p.latitude, p.longitude, p.altitude, origin),
    )
    return { full: fullPts, played: playedPts }
  }, [points, tMs, origin])

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
