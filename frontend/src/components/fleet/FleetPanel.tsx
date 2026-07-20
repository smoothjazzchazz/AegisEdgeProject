import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useOpsStore } from '@/hooks/useOpsStore'
import { DRONE_COLORS } from '@/types/telemetry'
import { pointsByDrone, sampleAt } from '@/lib/telemetry'
import { cn } from '@/lib/utils'

export function FleetPanel() {
  const drones = useOpsStore((s) => s.drones)
  const selectedIds = useOpsStore((s) => s.selectedIds)
  const points = useOpsStore((s) => s.points)
  const t = useOpsStore((s) => s.t)
  const toggleSelected = useOpsStore((s) => s.toggleSelected)
  const setSelectedIds = useOpsStore((s) => s.setSelectedIds)
  const [query, setQuery] = useState('')

  const byDrone = useMemo(
    () => pointsByDrone(points, drones.map((d) => d.aircraft_id)),
    [points, drones],
  )

  const filtered = drones.filter((d) =>
    d.aircraft_id.toLowerCase().includes(query.toLowerCase()),
  )

  return (
    <aside className="flex h-full w-[280px] shrink-0 flex-col border-r border-ops-border bg-ops-panel">
      <div className="border-b border-ops-border px-4 py-3">
        <div className="font-mono text-xs tracking-[0.2em] text-ops-accent uppercase">
          AegisEdge
        </div>
        <div className="mt-1 text-lg font-semibold text-ops-text">Fleet</div>
        <div className="mt-3 relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-ops-muted" />
          <Input
            className="pl-8"
            placeholder="Search callsign…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <div className="mt-2 flex gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1"
            onClick={() => setSelectedIds(drones.map((d) => d.aircraft_id))}
          >
            All
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="flex-1"
            onClick={() => setSelectedIds([])}
          >
            None
          </Button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {filtered.length === 0 && (
          <p className="px-2 py-6 text-center text-sm text-ops-muted">
            No aircraft loaded
          </p>
        )}
        {filtered.map((drone, i) => {
          const color = DRONE_COLORS[i % DRONE_COLORS.length]
          const active = selectedIds.includes(drone.aircraft_id)
          const series = byDrone.get(drone.aircraft_id) ?? []
          const sample = sampleAt(series, t)
          return (
            <button
              key={drone.aircraft_id}
              type="button"
              onClick={() => toggleSelected(drone.aircraft_id)}
              className={cn(
                'mb-1 w-full rounded-md border px-3 py-2.5 text-left transition-colors',
                active
                  ? 'border-ops-accent/40 bg-ops-accent/10'
                  : 'border-transparent hover:bg-ops-bg/60',
              )}
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2.5 w-2.5 rounded-full shrink-0"
                  style={{ background: color }}
                />
                <span className="font-mono text-sm font-medium">{drone.aircraft_id}</span>
              </div>
              <div className="mt-1.5 grid grid-cols-2 gap-x-2 gap-y-0.5 font-mono text-[11px] text-ops-muted">
                <span>ALT {sample ? sample.altitude.toFixed(0) : '—'} m</span>
                <span>HDG {sample ? sample.heading.toFixed(0) : '—'}°</span>
                <span className="col-span-2">
                  {drone.point_count.toLocaleString()} pts
                </span>
              </div>
            </button>
          )
        })}
      </div>
    </aside>
  )
}
