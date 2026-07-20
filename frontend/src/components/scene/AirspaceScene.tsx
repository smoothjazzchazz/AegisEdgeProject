import { Canvas } from '@react-three/fiber'
import { Grid, OrbitControls, PerspectiveCamera } from '@react-three/drei'
import { useMemo } from 'react'
import { useOpsStore } from '@/hooks/useOpsStore'
import { computeOrigin } from '@/lib/geo'
import { buildingsAtRisk, buildingsClassifiedDuringFlight } from '@/lib/buildings'
import { pointsByDrone, sampleAt } from '@/lib/telemetry'
import { DRONE_COLORS } from '@/types/telemetry'
import { TrajectoryLine } from './TrajectoryLine'
import { DroneMesh } from './DroneMesh'
import { RiskZoneMesh } from './RiskZoneMesh'
import { CorridorPath } from './CorridorPath'
import { BuildingMesh } from './BuildingMesh'
import { ClearanceLink } from './ClearanceLink'

function SceneContents() {
  const points = useOpsStore((s) => s.points)
  const selectedIds = useOpsStore((s) => s.selectedIds)
  const drones = useOpsStore((s) => s.drones)
  const t = useOpsStore((s) => s.t)
  const riskZones = useOpsStore((s) => s.riskZones)
  const corridor = useOpsStore((s) => s.corridor)
  const buildings = useOpsStore((s) => s.buildings)
  const buildingsVisible = useOpsStore((s) => s.buildingsVisible)
  const thresholdM = useOpsStore((s) => s.buildingThresholdM)

  const origin = useMemo(() => computeOrigin(points), [points])
  const byDrone = useMemo(
    () => pointsByDrone(points, selectedIds),
    [points, selectedIds],
  )

  const colorOf = (id: string) => {
    const idx = drones.findIndex((d) => d.aircraft_id === id)
    return DRONE_COLORS[(idx >= 0 ? idx : 0) % DRONE_COLORS.length]
  }

  // Flight-wide: red = collision (penetration), amber = within risk threshold
  const flightClass = useMemo(() => {
    const collisionIds = new Set<string>()
    const riskIds = new Set<string>()
    if (!buildings.length) return { collisionIds, riskIds }
    for (const id of selectedIds) {
      const series = byDrone.get(id) ?? []
      const partial = buildingsClassifiedDuringFlight(series, buildings, thresholdM)
      for (const bid of partial.collisionIds) collisionIds.add(bid)
      for (const bid of partial.riskIds) {
        if (!collisionIds.has(bid)) riskIds.add(bid)
      }
    }
    for (const id of collisionIds) riskIds.delete(id)
    return { collisionIds, riskIds }
  }, [buildings, selectedIds, byDrone, thresholdM])

  // Live clearance for EVERY selected aircraft (links + highlight union)
  const liveByDrone = useMemo(() => {
    const rows: {
      aircraftId: string
      sample: NonNullable<ReturnType<typeof sampleAt>>
      collisionIds: Set<string>
      riskIds: Set<string>
      nearest: NonNullable<ReturnType<typeof buildingsAtRisk>['nearest']>
    }[] = []
    if (!buildings.length) return rows
    for (const id of selectedIds) {
      const series = byDrone.get(id) ?? []
      const sample = sampleAt(series, t)
      if (!sample) continue
      const { collisionIds, riskIds, nearest } = buildingsAtRisk(
        sample.latitude,
        sample.longitude,
        sample.altitude,
        buildings,
        thresholdM,
      )
      if (!nearest) continue
      rows.push({ aircraftId: id, sample, collisionIds, riskIds, nearest })
    }
    return rows
  }, [buildings, selectedIds, byDrone, t, thresholdM])

  const collisionIds = useMemo(() => {
    const s = new Set(flightClass.collisionIds)
    for (const row of liveByDrone) {
      for (const id of row.collisionIds) s.add(id)
    }
    return s
  }, [flightClass.collisionIds, liveByDrone])

  const riskIds = useMemo(() => {
    const s = new Set(flightClass.riskIds)
    for (const row of liveByDrone) {
      for (const id of row.riskIds) s.add(id)
    }
    for (const id of collisionIds) s.delete(id)
    return s
  }, [flightClass.riskIds, liveByDrone, collisionIds])

  return (
    <>
      <color attach="background" args={['#0b0f14']} />
      <ambientLight intensity={0.55} />
      <directionalLight position={[5, 10, 5]} intensity={0.85} />
      <PerspectiveCamera makeDefault position={[3.5, 2.8, 3.5]} fov={50} />
      <OrbitControls makeDefault enableDamping dampingFactor={0.08} maxPolarAngle={Math.PI / 2.05} />
      <Grid
        infiniteGrid
        fadeDistance={40}
        sectionColor="#1e2a36"
        cellColor="#151c24"
        sectionSize={1}
        cellSize={0.2}
        position={[0, 0, 0]}
      />
      <axesHelper args={[1.5]} />

      {selectedIds.map((id) => {
        const series = byDrone.get(id) ?? []
        if (!series.length) return null
        const color = colorOf(id)
        const sample = sampleAt(series, t)
        return (
          <group key={id}>
            <TrajectoryLine points={series} color={color} tMs={t} origin={origin} />
            {sample && <DroneMesh sample={sample} color={color} origin={origin} selected />}
          </group>
        )
      })}

      {buildingsVisible &&
        buildings.map((b) => (
          <BuildingMesh
            key={b.id}
            building={b}
            origin={origin}
            hot={collisionIds.has(b.id)}
            hit={riskIds.has(b.id)}
          />
        ))}

      {buildingsVisible &&
        liveByDrone.map((row) => (
          <ClearanceLink
            key={`link-${row.aircraftId}`}
            droneLat={row.sample.latitude}
            droneLon={row.sample.longitude}
            droneAlt={row.sample.altitude}
            nearest={row.nearest}
            buildings={buildings}
            origin={origin}
            thresholdM={thresholdM}
          />
        ))}

      {riskZones
        .filter((z) => z.density > 5)
        .map((zone, i) => (
          <RiskZoneMesh key={i} zone={zone} origin={origin} />
        ))}

      {corridor && (
        <CorridorPath
          direct={corridor.direct_path}
          optimized={corridor.optimized_path}
          origin={origin}
        />
      )}
    </>
  )
}

function BuildingHud() {
  const buildings = useOpsStore((s) => s.buildings)
  const selectedIds = useOpsStore((s) => s.selectedIds)
  const points = useOpsStore((s) => s.points)
  const t = useOpsStore((s) => s.t)
  const buildingsVisible = useOpsStore((s) => s.buildingsVisible)
  const thresholdM = useOpsStore((s) => s.buildingThresholdM)

  const readout = useMemo(() => {
    if (!buildingsVisible || !buildings.length || !selectedIds.length) return null
    const byDroneMap = pointsByDrone(points, selectedIds)

    const collisionIds = new Set<string>()
    const riskIds = new Set<string>()
    let bestLive: {
      callsign: string
      nearest: NonNullable<ReturnType<typeof buildingsAtRisk>['nearest']>
    } | null = null

    for (const id of selectedIds) {
      const series = byDroneMap.get(id) ?? []
      const partial = buildingsClassifiedDuringFlight(series, buildings, thresholdM)
      for (const bid of partial.collisionIds) collisionIds.add(bid)
      for (const bid of partial.riskIds) riskIds.add(bid)

      const sample = sampleAt(series, t)
      if (!sample) continue
      const live = buildingsAtRisk(
        sample.latitude,
        sample.longitude,
        sample.altitude,
        buildings,
        thresholdM,
      )
      for (const bid of live.collisionIds) collisionIds.add(bid)
      for (const bid of live.riskIds) riskIds.add(bid)
      if (
        live.nearest &&
        (!bestLive || live.nearest.clearance_m < bestLive.nearest.clearance_m)
      ) {
        bestLive = { callsign: id, nearest: live.nearest }
      }
    }
    for (const id of collisionIds) riskIds.delete(id)
    if (!bestLive) return null

    return {
      nearest: bestLive.nearest,
      callsign: bestLive.callsign,
      collisionCount: collisionIds.size,
      riskCount: riskIds.size,
      liveCollision: bestLive.nearest.penetrating,
      selectedCount: selectedIds.length,
    }
  }, [buildings, buildingsVisible, selectedIds, points, t, thresholdM])

  if (!readout?.nearest) {
    if (!buildings.length) return null
    return (
      <div className="pointer-events-none absolute left-3 top-3 rounded border border-ops-border bg-ops-panel/90 px-3 py-2 font-mono text-[11px] text-ops-muted">
        {buildings.length} OSM solids · threshold {thresholdM} m
      </div>
    )
  }

  const { nearest, callsign, collisionCount, riskCount, liveCollision, selectedCount } =
    readout
  const danger = nearest.penetrating || liveCollision
  const label = nearest.penetrating
    ? 'COLLISION'
    : nearest.clearance_m < thresholdM
      ? 'IN RISK ZONE'
      : nearest.overFootprint
        ? 'OVER ROOF'
        : 'WALL SEP'

  return (
    <div
      className={`pointer-events-none absolute left-3 top-3 rounded border px-3 py-2 font-mono text-[11px] ${
        danger
          ? 'border-ops-danger/60 bg-ops-danger/15 text-ops-danger'
          : nearest.clearance_m < thresholdM
            ? 'border-ops-warn/60 bg-ops-warn/10 text-ops-warn'
            : 'border-ops-border bg-ops-panel/90 text-ops-text'
      }`}
    >
      <div className="text-[10px] uppercase tracking-wider text-ops-muted">
        closest: {callsign} · {label} · {selectedCount} links
      </div>
      <div className="mt-0.5 text-sm">
        clr {nearest.clearance_m.toFixed(1)} m
        <span className="text-ops-muted"> · horiz {nearest.horizontal_m.toFixed(1)} m</span>
      </div>
      <div className="text-ops-muted">
        collisions {collisionCount} · risk {riskCount} @ {thresholdM} m
      </div>
      <div className="mt-1 flex gap-2 text-[10px]">
        <span className="text-ops-danger">● collision</span>
        <span className="text-ops-warn">● within threshold</span>
      </div>
    </div>
  )
}

export function AirspaceScene() {
  const points = useOpsStore((s) => s.points)

  return (
    <div className="relative h-full w-full bg-ops-bg">
      {points.length === 0 ? (
        <div className="flex h-full items-center justify-center text-ops-muted">
          <div className="text-center">
            <p className="font-mono text-sm tracking-widest uppercase text-ops-accent">
              Airspace offline
            </p>
            <p className="mt-2 text-sm">Load demo data or upload a CSV to begin.</p>
          </div>
        </div>
      ) : (
        <>
          <Canvas gl={{ antialias: true }} dpr={[1, 2]}>
            <SceneContents />
          </Canvas>
          <BuildingHud />
        </>
      )}
    </div>
  )
}
