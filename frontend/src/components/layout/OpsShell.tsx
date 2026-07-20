import type { ReactNode } from 'react'
import {
  AlertTriangle,
  Building2,
  ChevronRight,
  Database,
  PanelBottomClose,
  PanelBottomOpen,
  Route,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { FleetPanel } from '@/components/fleet/FleetPanel'
import { AirspaceScene } from '@/components/scene/AirspaceScene'
import { ReplayControls } from '@/components/timeline/ReplayControls'
import { CollisionPanel } from '@/components/drawer/CollisionPanel'
import { CorridorPanel } from '@/components/drawer/CorridorPanel'
import { DataPanel } from '@/components/drawer/DataPanel'
import { BuildingsPanel } from '@/components/drawer/BuildingsPanel'
import { ChartsStrip } from '@/components/charts/ChartsStrip'
import { useOpsStore } from '@/hooks/useOpsStore'
import type { DrawerMode } from '@/types/telemetry'
import { cn } from '@/lib/utils'

interface Props {
  onDataChanged: () => Promise<void>
}

export function OpsShell({ onDataChanged }: Props) {
  const drawer = useOpsStore((s) => s.drawer)
  const setDrawer = useOpsStore((s) => s.setDrawer)
  const chartsOpen = useOpsStore((s) => s.chartsOpen)
  const setChartsOpen = useOpsStore((s) => s.setChartsOpen)
  const error = useOpsStore((s) => s.error)
  const loading = useOpsStore((s) => s.loading)
  const wsConnected = useOpsStore((s) => s.wsConnected)

  const toggle = (mode: DrawerMode) => {
    setDrawer(drawer === mode ? null : mode)
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Top status bar */}
      <header className="flex h-10 shrink-0 items-center justify-between border-b border-ops-border bg-ops-panel px-3">
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs tracking-[0.25em] text-ops-accent uppercase">
            AegisEdge ATC
          </span>
          <span className="text-ops-border">|</span>
          <span className="font-mono text-[11px] text-ops-muted">ops console</span>
          {loading && (
            <span className="font-mono text-[11px] text-ops-warn animate-pulse">working…</span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <span
            className={cn(
              'mr-2 flex items-center gap-1 font-mono text-[10px]',
              wsConnected ? 'text-ops-safe' : 'text-ops-muted',
            )}
            title="WebSocket /ws/telemetry"
          >
            {wsConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
            WS
          </span>
          <ToolBtn
            active={drawer === 'collision'}
            onClick={() => toggle('collision')}
            icon={<AlertTriangle className="h-4 w-4" />}
            label="Collision"
          />
          <ToolBtn
            active={drawer === 'corridor'}
            onClick={() => toggle('corridor')}
            icon={<Route className="h-4 w-4" />}
            label="Corridor"
          />
          <ToolBtn
            active={drawer === 'buildings'}
            onClick={() => toggle('buildings')}
            icon={<Building2 className="h-4 w-4" />}
            label="Buildings"
          />
          <ToolBtn
            active={drawer === 'data'}
            onClick={() => toggle('data')}
            icon={<Database className="h-4 w-4" />}
            label="Data"
          />
          <Button
            size="icon"
            variant="ghost"
            onClick={() => setChartsOpen(!chartsOpen)}
            title="Toggle charts"
          >
            {chartsOpen ? (
              <PanelBottomClose className="h-4 w-4" />
            ) : (
              <PanelBottomOpen className="h-4 w-4" />
            )}
          </Button>
        </div>
      </header>

      {error && (
        <div className="flex items-center justify-between bg-ops-danger/15 px-4 py-1.5 text-xs text-ops-danger">
          <span>{error}</span>
          <button type="button" onClick={() => useOpsStore.getState().setError(null)}>
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <div className="flex min-h-0 flex-1">
        <FleetPanel />

        <div className="relative flex min-w-0 flex-1 flex-col">
          <div className="min-h-0 flex-1">
            <AirspaceScene />
          </div>
          <ChartsStrip />
          <ReplayControls />
        </div>

        {/* Right tool drawer */}
        <div
          className={cn(
            'shrink-0 overflow-hidden border-l border-ops-border bg-ops-panel transition-[width] duration-200',
            drawer ? 'w-[320px]' : 'w-0 border-l-0',
          )}
        >
          {drawer && (
            <div className="flex h-full w-[320px] flex-col">
              <div className="flex items-center justify-between border-b border-ops-border px-3 py-2">
                <span className="font-mono text-[11px] uppercase tracking-wider text-ops-muted">
                  {drawer}
                </span>
                <Button size="icon" variant="ghost" onClick={() => setDrawer(null)}>
                  <ChevronRight className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex-1 overflow-y-auto">
                {drawer === 'collision' && <CollisionPanel />}
                {drawer === 'corridor' && <CorridorPanel />}
                {drawer === 'buildings' && <BuildingsPanel />}
                {drawer === 'data' && <DataPanel onDataChanged={onDataChanged} />}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ToolBtn({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: ReactNode
  label: string
}) {
  return (
    <Button
      size="sm"
      variant={active ? 'default' : 'ghost'}
      onClick={onClick}
      className="gap-1.5"
    >
      {icon}
      <span className="hidden sm:inline">{label}</span>
    </Button>
  )
}
