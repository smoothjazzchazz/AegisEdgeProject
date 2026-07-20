import { Line } from '@react-three/drei'
import { useMemo } from 'react'
import { toLocal, type Origin } from '@/lib/geo'
import { closestFootprintPoint, type ClearanceResult } from '@/lib/buildings'
import type { OsmBuilding } from '@/types/telemetry'

interface Props {
  droneLat: number
  droneLon: number
  droneAlt: number
  nearest: ClearanceResult
  buildings: OsmBuilding[]
  origin: Origin
  thresholdM: number
}

/** Line from drone to nearest building wall/roof attach point. */
export function ClearanceLink({
  droneLat,
  droneLon,
  droneAlt,
  nearest,
  buildings,
  origin,
  thresholdM,
}: Props) {
  const points = useMemo(() => {
    const b = buildings.find((x) => x.id === nearest.buildingId)
    if (!b || !b.footprint.length) return null

    const wall = closestFootprintPoint(droneLat, droneLon, b.footprint)
    const attachAlt = nearest.overFootprint
      ? b.height_m
      : Math.min(Math.max(droneAlt, 0), b.height_m)

    const a = toLocal(droneLat, droneLon, droneAlt, origin)
    const c = toLocal(wall.lat, wall.lon, attachAlt, origin)
    return [a, c] as [[number, number, number], [number, number, number]]
  }, [droneLat, droneLon, droneAlt, nearest, buildings, origin])

  if (!points) return null

  const danger = nearest.penetrating || nearest.clearance_m < thresholdM

  return (
    <Line
      points={points}
      color={danger ? '#c45c5c' : '#c4a35a'}
      lineWidth={2}
      dashed
      dashSize={0.06}
      gapSize={0.04}
    />
  )
}
