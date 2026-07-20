import { Pause, Play, Gauge } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { useOpsStore } from '@/hooks/useOpsStore'

function formatTime(ms: number) {
  if (!ms) return '—'
  const d = new Date(ms)
  return d.toISOString().replace('T', ' ').replace(/\.\d+Z$/, 'Z')
}

export function ReplayControls() {
  const t = useOpsStore((s) => s.t)
  const tMin = useOpsStore((s) => s.tMin)
  const tMax = useOpsStore((s) => s.tMax)
  const playing = useOpsStore((s) => s.playing)
  const speed = useOpsStore((s) => s.speed)
  const setT = useOpsStore((s) => s.setT)
  const setPlaying = useOpsStore((s) => s.setPlaying)
  const setSpeed = useOpsStore((s) => s.setSpeed)

  const span = Math.max(tMax - tMin, 1)
  const pct = ((t - tMin) / span) * 100

  return (
    <div className="flex h-14 shrink-0 items-center gap-3 border-t border-ops-border bg-ops-panel px-4">
      <Button
        size="icon"
        variant="secondary"
        onClick={() => setPlaying(!playing)}
        aria-label={playing ? 'Pause' : 'Play'}
      >
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </Button>

      <div className="flex items-center gap-1">
        {[1, 2, 5].map((s) => (
          <Button
            key={s}
            size="sm"
            variant={speed === s ? 'default' : 'ghost'}
            onClick={() => setSpeed(s)}
            className="font-mono"
          >
            {s}x
          </Button>
        ))}
      </div>

      <div className="flex min-w-0 flex-1 items-center gap-3">
        <span className="hidden shrink-0 font-mono text-[10px] text-ops-muted sm:block w-40 truncate">
          {formatTime(t)}
        </span>
        <Slider
          className="flex-1"
          min={tMin}
          max={tMax}
          step={1000}
          value={[t]}
          onValueChange={([v]) => {
            setPlaying(false)
            setT(v)
          }}
        />
        <span className="hidden shrink-0 font-mono text-[10px] text-ops-muted lg:block w-40 truncate text-right">
          {formatTime(tMax)}
        </span>
      </div>

      <div className="flex items-center gap-1.5 font-mono text-xs text-ops-muted">
        <Gauge className="h-3.5 w-3.5" />
        {pct.toFixed(0)}%
      </div>
    </div>
  )
}
