import { useMemo, type ReactNode } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { useOpsStore } from '@/hooks/useOpsStore'
import { pointsByDrone } from '@/lib/telemetry'
import { DRONE_COLORS } from '@/types/telemetry'

/** Align selected drones onto a shared time axis (primary drone's samples). */
function multiSeries(
  byDrone: Map<string, { timestamp: string; altitude: number; heading: number }[]>,
  selectedIds: string[],
  field: 'altitude' | 'heading',
): Record<string, number | string>[] {
  const primary = selectedIds[0]
  if (!primary) return []
  const series = byDrone.get(primary) ?? []
  return series.map((p) => {
    const row: Record<string, number | string> = {
      t: new Date(p.timestamp).getTime(),
      label: p.timestamp.slice(11, 19),
    }
    const target = new Date(p.timestamp).getTime()
    for (const id of selectedIds) {
      const s = byDrone.get(id) ?? []
      if (!s.length) continue
      let best = s[0]
      let bestD = Infinity
      for (const q of s) {
        const d = Math.abs(new Date(q.timestamp).getTime() - target)
        if (d < bestD) {
          bestD = d
          best = q
        }
      }
      row[id] = best[field]
    }
    return row
  })
}

export function ChartsStrip() {
  const points = useOpsStore((s) => s.points)
  const selectedIds = useOpsStore((s) => s.selectedIds)
  const drones = useOpsStore((s) => s.drones)
  const t = useOpsStore((s) => s.t)
  const chartsOpen = useOpsStore((s) => s.chartsOpen)
  const collision = useOpsStore((s) => s.collision)

  const byDrone = useMemo(
    () => pointsByDrone(points, selectedIds),
    [points, selectedIds],
  )

  const colorOf = (id: string) => {
    const idx = drones.findIndex((d) => d.aircraft_id === id)
    return DRONE_COLORS[(idx >= 0 ? idx : 0) % DRONE_COLORS.length]
  }

  const altSeries = useMemo(
    () => multiSeries(byDrone, selectedIds, 'altitude'),
    [byDrone, selectedIds],
  )

  const headingSeries = useMemo(
    () => multiSeries(byDrone, selectedIds, 'heading'),
    [byDrone, selectedIds],
  )

  const collisionSeries = useMemo(() => {
    if (!collision) return []
    return collision.samples.map((s) => ({
      t: new Date(s.timestamp).getTime(),
      label: s.timestamp.slice(11, 19),
      distance: s.distance_m,
      risk: s.risk * 100,
    }))
  }, [collision])

  const cursorLabel = useMemo(() => {
    if (!collisionSeries.length) return null
    return collisionSeries.reduce((best, row) =>
      Math.abs((row.t as number) - t) < Math.abs((best.t as number) - t) ? row : best,
    ).label
  }, [collisionSeries, t])

  if (!chartsOpen) return null

  return (
    <div className="grid h-52 shrink-0 grid-cols-2 gap-px border-t border-ops-border bg-ops-border lg:grid-cols-4">
      <ChartCard title="Altitude (m)">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={altSeries}>
            <XAxis dataKey="label" hide />
            <YAxis stroke="#7a8b9a" fontSize={10} width={36} />
            <Tooltip
              contentStyle={{ background: '#121820', border: '1px solid #1e2a36' }}
              labelStyle={{ color: '#7a8b9a' }}
            />
            {selectedIds.map((id) => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                name={id}
                stroke={colorOf(id)}
                dot={false}
                strokeWidth={1.5}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Heading (°)">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={headingSeries}>
            <XAxis dataKey="label" hide />
            <YAxis stroke="#7a8b9a" fontSize={10} width={36} domain={[0, 360]} />
            <Tooltip
              contentStyle={{ background: '#121820', border: '1px solid #1e2a36' }}
            />
            {selectedIds.map((id) => (
              <Line
                key={id}
                type="monotone"
                dataKey={id}
                name={id}
                stroke={colorOf(id)}
                dot={false}
                strokeWidth={1.5}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title={collision ? 'Separation (m)' : 'Separation — run Collision'}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={collisionSeries}>
            <XAxis dataKey="label" hide />
            <YAxis stroke="#7a8b9a" fontSize={10} width={40} />
            <Tooltip
              contentStyle={{ background: '#121820', border: '1px solid #1e2a36' }}
            />
            <Line
              type="monotone"
              dataKey="distance"
              name="distance"
              stroke="#5b8fa8"
              dot={false}
              strokeWidth={1.5}
              isAnimationActive={false}
            />
            {cursorLabel && (
              <ReferenceLine x={cursorLabel} stroke="#c4a35a" strokeDasharray="3 3" />
            )}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title={collision ? 'Collision risk (%)' : 'Risk — run Collision'}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={collisionSeries}>
            <XAxis dataKey="label" hide />
            <YAxis stroke="#7a8b9a" fontSize={10} width={36} domain={[0, 100]} />
            <Tooltip
              contentStyle={{ background: '#121820', border: '1px solid #1e2a36' }}
            />
            <Line
              type="monotone"
              dataKey="risk"
              name="risk"
              stroke="#c45c5c"
              dot={false}
              strokeWidth={1.5}
              isAnimationActive={false}
              fill="#c45c5c"
            />
            {cursorLabel && (
              <ReferenceLine x={cursorLabel} stroke="#c4a35a" strokeDasharray="3 3" />
            )}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col bg-ops-panel px-2 pb-2 pt-1.5">
      <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-ops-muted">
        {title}
      </div>
      <div className="min-h-0 flex-1">{children}</div>
    </div>
  )
}
