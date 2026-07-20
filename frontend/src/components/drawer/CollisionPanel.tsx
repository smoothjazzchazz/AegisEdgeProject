import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { api } from '@/lib/api'
import { useOpsStore } from '@/hooks/useOpsStore'

export function CollisionPanel() {
  const drones = useOpsStore((s) => s.drones)
  const collision = useOpsStore((s) => s.collision)
  const setCollision = useOpsStore((s) => s.setCollision)
  const setError = useOpsStore((s) => s.setError)
  const setLoading = useOpsStore((s) => s.setLoading)

  const [droneA, setDroneA] = useState('')
  const [droneB, setDroneB] = useState('')
  const [threshold, setThreshold] = useState(100)

  useEffect(() => {
    if (drones.length && !droneA) {
      setDroneA(drones[0].aircraft_id)
      setDroneB(drones[1]?.aircraft_id ?? drones[0].aircraft_id)
    }
  }, [drones, droneA])

  const run = async () => {
    if (!droneA || !droneB) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.collision(droneA, droneB, threshold)
      setCollision(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setCollision(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h3 className="text-sm font-semibold text-ops-text">Collision Analysis</h3>
        <p className="mt-1 text-xs text-ops-muted">
          Pairwise 3D separation and risk relative to threshold.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Aircraft A</Label>
        <select
          className="flex h-9 w-full rounded-md border border-ops-border bg-ops-bg px-3 text-sm text-ops-text"
          value={droneA}
          onChange={(e) => setDroneA(e.target.value)}
        >
          {drones.map((d) => (
            <option key={d.aircraft_id} value={d.aircraft_id}>
              {d.aircraft_id}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <Label>Aircraft B</Label>
        <select
          className="flex h-9 w-full rounded-md border border-ops-border bg-ops-bg px-3 text-sm text-ops-text"
          value={droneB}
          onChange={(e) => setDroneB(e.target.value)}
        >
          {drones.map((d) => (
            <option key={d.aircraft_id} value={d.aircraft_id}>
              {d.aircraft_id}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <Label>Threshold — {threshold} m</Label>
        <Slider
          min={10}
          max={1000}
          step={10}
          value={[threshold]}
          onValueChange={([v]) => setThreshold(v)}
        />
      </div>

      <Button className="w-full" onClick={run}>
        Run Analysis
      </Button>

      {collision && (
        <div className="grid grid-cols-2 gap-2 rounded-md border border-ops-border bg-ops-bg p-3 font-mono text-xs">
          <Stat label="Min dist" value={`${collision.min_distance_m.toFixed(1)} m`} alert />
          <Stat label="Avg dist" value={`${collision.avg_distance_m.toFixed(1)} m`} />
          <Stat label="Max risk" value={`${(collision.max_risk * 100).toFixed(0)}%`} warn />
          <Stat label="Time at risk" value={`${collision.time_at_risk_pct.toFixed(1)}%`} />
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
