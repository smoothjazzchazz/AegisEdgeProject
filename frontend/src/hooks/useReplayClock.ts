import { useEffect, useRef } from 'react'
import { useOpsStore } from '@/hooks/useOpsStore'
import { orbitDraggingRef, UI_T_INTERVAL_MS, visualTRef } from '@/lib/replayClock'

/** Client-owned replay clock — advances visual t every frame; publishes UI t throttled. */
export function useReplayClock() {
  const playing = useOpsStore((s) => s.playing)
  const speed = useOpsStore((s) => s.speed)
  const tMax = useOpsStore((s) => s.tMax)
  const setT = useOpsStore((s) => s.setT)
  const setPlaying = useOpsStore((s) => s.setPlaying)
  const raf = useRef<number>(0)
  const last = useRef<number>(0)
  const lastUi = useRef<number>(0)

  useEffect(() => {
    if (!playing) {
      last.current = 0
      lastUi.current = 0
      // Flush high-rate time so slider/HUD match the scene after pause
      const vt = visualTRef.current
      const st = useOpsStore.getState().t
      if (vt > st) setT(vt)
      return
    }

    // Keep visual clock across speed changes; only catch up if store was scrubbed ahead
    const storeT = useOpsStore.getState().t
    if (storeT > visualTRef.current) visualTRef.current = storeT

    const tick = (now: number) => {
      if (orbitDraggingRef.current) {
        // Freeze clock; reset dt baseline so resume doesn't jump
        last.current = now
        raf.current = requestAnimationFrame(tick)
        return
      }

      if (!last.current) last.current = now
      const dt = now - last.current
      last.current = now
      const state = useOpsStore.getState()
      const advanced = visualTRef.current + dt * state.speed

      if (advanced >= state.tMax) {
        visualTRef.current = state.tMax
        setT(state.tMax)
        setPlaying(false)
        return
      }

      visualTRef.current = advanced
      if (now - lastUi.current >= UI_T_INTERVAL_MS) {
        lastUi.current = now
        setT(advanced)
      }
      raf.current = requestAnimationFrame(tick)
    }

    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [playing, speed, tMax, setT, setPlaying])
}
