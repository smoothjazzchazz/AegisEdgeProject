import { useEffect, useState } from 'react'
import { Building2, Eye, EyeOff, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { api } from '@/lib/api'
import { useOpsStore } from '@/hooks/useOpsStore'

export function BuildingsPanel() {
  const drones = useOpsStore((s) => s.drones)
  const buildings = useOpsStore((s) => s.buildings)
  const buildingsVisible = useOpsStore((s) => s.buildingsVisible)
  const buildingRisk = useOpsStore((s) => s.buildingRisk)
  const threshold = useOpsStore((s) => s.buildingThresholdM)
  const setBuildings = useOpsStore((s) => s.setBuildings)
  const setBuildingsVisible = useOpsStore((s) => s.setBuildingsVisible)
  const setBuildingRisk = useOpsStore((s) => s.setBuildingRisk)
  const setBuildingThresholdM = useOpsStore((s) => s.setBuildingThresholdM)
  const setLoading = useOpsStore((s) => s.setLoading)
  const setError = useOpsStore((s) => s.setError)

  const [aircraftId, setAircraftId] = useState('')

  useEffect(() => {
    if (drones.length && !aircraftId) setAircraftId(drones[0].aircraft_id)
  }, [drones, aircraftId])

  const loadOsm = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.loadBuildings(0.004)
      setBuildings(res.buildings)
      setBuildingsVisible(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const clear = async () => {
    setLoading(true)
    try {
      await api.clearBuildings()
      setBuildings([])
      setBuildingRisk(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const runRisk = async () => {
    if (!aircraftId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.buildingRisk(aircraftId, threshold)
      setBuildingRisk(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setBuildingRisk(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h3 className="text-sm font-semibold text-ops-text">OSM Buildings</h3>
        <p className="mt-1 text-xs text-ops-muted">
          Red = flight path intersects the building solid (segment∩prism). Amber =
          path comes within your clearance threshold. Red overrides amber.
        </p>
      </div>

      <Button className="w-full" onClick={loadOsm}>
        <Building2 className="h-4 w-4" />
        Load buildings for airspace
      </Button>

      <div className="flex gap-2">
        <Button
          variant="outline"
          className="flex-1"
          onClick={() => setBuildingsVisible(!buildingsVisible)}
          disabled={!buildings.length}
        >
          {buildingsVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          {buildingsVisible ? 'Hide' : 'Show'}
        </Button>
        <Button variant="ghost" onClick={clear} disabled={!buildings.length}>
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      <div className="rounded-md border border-ops-border bg-ops-bg p-3 font-mono text-xs text-ops-muted">
        {buildings.length
          ? `${buildings.length} solids cached`
          : 'No buildings loaded'}
      </div>

      <div className="border-t border-ops-border pt-4 space-y-3">
        <h4 className="text-xs font-semibold uppercase tracking-wide text-ops-muted">
          Clearance threshold
        </h4>
        <div className="space-y-2">
          <Label>Risk threshold — {threshold} m</Label>
          <Slider
            min={5}
            max={100}
            step={5}
            value={[threshold]}
            onValueChange={([v]) => setBuildingThresholdM(v)}
          />
          <p className="text-[11px] text-ops-muted">
            Amber highlights when clearance &lt; this value. Red only on solid penetration.
          </p>
        </div>

        <div className="space-y-2">
          <Label>Aircraft (stats report)</Label>
          <select
            className="flex h-9 w-full rounded-md border border-ops-border bg-ops-bg px-3 text-sm text-ops-text"
            value={aircraftId}
            onChange={(e) => setAircraftId(e.target.value)}
          >
            {drones.map((d) => (
              <option key={d.aircraft_id} value={d.aircraft_id}>
                {d.aircraft_id}
              </option>
            ))}
          </select>
        </div>
        <Button
          className="w-full"
          variant="danger"
          onClick={runRisk}
          disabled={!buildings.length || !aircraftId}
        >
          Analyze building risk
        </Button>
      </div>

      {buildingRisk && (
        <div className="grid grid-cols-2 gap-2 rounded-md border border-ops-border bg-ops-bg p-3 font-mono text-xs">
          <Stat
            label="Min clearance"
            value={`${buildingRisk.min_clearance_m.toFixed(1)} m`}
            alert={buildingRisk.min_clearance_m < threshold}
          />
          <Stat
            label="Time at risk"
            value={`${buildingRisk.time_at_risk_pct.toFixed(1)}%`}
            warn
          />
          <Stat
            label="Penetrations"
            value={`${buildingRisk.penetration_count}`}
            alert={buildingRisk.penetration_count > 0}
          />
          <Stat
            label="Checked"
            value={`${buildingRisk.buildings_checked}`}
          />
          <Stat
            label="Path collisions"
            value={`${buildingRisk.trajectory_collisions ?? buildingRisk.penetration_count}`}
            alert={(buildingRisk.trajectory_collisions ?? 0) > 0}
          />
          <Stat
            label="Path risk hits"
            value={`${buildingRisk.trajectory_risk_buildings ?? 0}`}
            warn
          />
        </div>
      )}
    </div>
  )
}

function Stat({
  label,
  value,
  alert,
  warn,
}: {
  label: string
  value: string
  alert?: boolean
  warn?: boolean
}) {
  return (
    <div>
      <div className="text-ops-muted uppercase tracking-wide text-[10px]">{label}</div>
      <div className={alert ? 'text-ops-danger' : warn ? 'text-ops-warn' : 'text-ops-text'}>
        {value}
      </div>
    </div>
  )
}
