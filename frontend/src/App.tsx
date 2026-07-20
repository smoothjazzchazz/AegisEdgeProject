import { useCallback, useEffect } from 'react'
import { OpsShell } from '@/components/layout/OpsShell'
import { useReplayClock } from '@/hooks/useReplayClock'
import { useTelemetrySocket } from '@/hooks/useTelemetrySocket'
import { useOpsStore } from '@/hooks/useOpsStore'
import { api } from '@/lib/api'

export default function App() {
  useReplayClock()
  useTelemetrySocket(true)

  const setFleet = useOpsStore((s) => s.setFleet)
  const setPoints = useOpsStore((s) => s.setPoints)
  const setError = useOpsStore((s) => s.setError)
  const setLoading = useOpsStore((s) => s.setLoading)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const fleet = await api.fleet()
      setFleet(fleet.drones, fleet.t_min, fleet.t_max)
      const ids = fleet.drones.map((d) => d.aircraft_id)
      const traj = await api.trajectories(ids)
      setPoints(traj.points)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [setFleet, setPoints, setError, setLoading])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return <OpsShell onDataChanged={refresh} />
}
