import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { api } from '@/lib/api'
import { useOpsStore } from '@/hooks/useOpsStore'

export function CorridorPanel() {
  const selectedIds = useOpsStore((s) => s.selectedIds)
  const points = useOpsStore((s) => s.points)
  const buildings = useOpsStore((s) => s.buildings)
  const corridor = useOpsStore((s) => s.corridor)
  const setCorridor = useOpsStore((s) => s.setCorridor)
  const setRiskZones = useOpsStore((s) => s.setRiskZones)
  const setBuildings = useOpsStore((s) => s.setBuildings)
  const setError = useOpsStore((s) => s.setError)
  const setLoading = useOpsStore((s) => s.setLoading)

  const defaults = (() => {
    if (!points.length) {
      return { startLat: 40.78, startLon: -73.97, endLat: 40.79, endLon: -73.96 }
    }
    const lats = points.map((p) => p.latitude)
    const lons = points.map((p) => p.longitude)
    return {
      startLat: Math.min(...lats),
      startLon: Math.min(...lons),
      endLat: Math.max(...lats),
      endLon: Math.max(...lons),
    }
  })()

  const [startLat, setStartLat] = useState(defaults.startLat)
  const [startLon, setStartLon] = useState(defaults.startLon)
  const [endLat, setEndLat] = useState(defaults.endLat)
  const [endLon, setEndLon] = useState(defaults.endLon)
  const [altitude, setAltitude] = useState(100)

  const ensureBuildings = async () => {
    if (buildings.length) return
    const res = await api.loadBuildings(0.004)
    setBuildings(res.buildings)
  }

  const run = async () => {
    setLoading(true)
    setError(null)
    try {
      await ensureBuildings()
      const res = await api.corridor({
        start: { lat: startLat, lon: startLon },
        end: { lat: endLat, lon: endLon },
        altitude_m: altitude,
        drone_ids: selectedIds.length ? selectedIds : undefined,
      })
      setCorridor(res)
      setRiskZones(res.zones)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setCorridor(null)
    } finally {
      setLoading(false)
    }
  }

  const clear = () => {
    setCorridor(null)
    setRiskZones([])
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h3 className="text-sm font-semibold text-ops-text">Safe Corridor</h3>
        <p className="mt-1 text-xs text-ops-muted">
          Avoids congestion zones and OSM building solids (climb / lateral deflect).
          Loads buildings automatically if none are cached.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <Label>Start lat</Label>
          <Input
            type="number"
            step={0.0001}
            value={startLat}
            onChange={(e) => setStartLat(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1">
          <Label>Start lon</Label>
          <Input
            type="number"
            step={0.0001}
            value={startLon}
            onChange={(e) => setStartLon(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1">
          <Label>End lat</Label>
          <Input
            type="number"
            step={0.0001}
            value={endLat}
            onChange={(e) => setEndLat(Number(e.target.value))}
          />
        </div>
        <div className="space-y-1">
          <Label>End lon</Label>
          <Input
            type="number"
            step={0.0001}
            value={endLon}
            onChange={(e) => setEndLon(Number(e.target.value))}
          />
        </div>
      </div>

      <div className="space-y-1">
        <Label>Preferred altitude (m)</Label>
        <Input
          type="number"
          step={10}
          value={altitude}
          onChange={(e) => setAltitude(Number(e.target.value))}
        />
      </div>

      <div className="flex gap-2">
        <Button className="flex-1" variant="safe" onClick={run}>
          Generate
        </Button>
        <Button variant="ghost" onClick={clear}>
          Clear
        </Button>
      </div>

      {corridor && (
        <div className="space-y-2 rounded-md border border-ops-border bg-ops-bg p-3 font-mono text-xs">
          <Row label="Direct" value={`${corridor.direct_length_km.toFixed(2)} km`} />
          <Row
            label="Optimized"
            value={`${corridor.optimized_length_km.toFixed(2)} km (+${corridor.path_difference_pct.toFixed(1)}%)`}
          />
          <Row label="Avg alt" value={`${corridor.avg_altitude.toFixed(0)} m`} />
          <Row label="Traffic zones" value={`${corridor.risk_zones_avoided}`} />
          <Row
            label="Buildings avoided"
            value={`${corridor.buildings_avoided ?? 0} / ${corridor.buildings_loaded ?? 0} loaded`}
          />
        </div>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-ops-muted">{label}</span>
      <span className="text-ops-text text-right">{value}</span>
    </div>
  )
}
