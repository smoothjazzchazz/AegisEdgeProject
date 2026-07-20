import { useEffect, useRef } from 'react'
import { useOpsStore } from '@/hooks/useOpsStore'

/** Client-owned replay clock — advances t while playing. */
export function useReplayClock() {
  const playing = useOpsStore((s) => s.playing)
  const speed = useOpsStore((s) => s.speed)
  const tMax = useOpsStore((s) => s.tMax)
  const setT = useOpsStore((s) => s.setT)
  const setPlaying = useOpsStore((s) => s.setPlaying)
  const raf = useRef<number>(0)
  const last = useRef<number>(0)

  useEffect(() => {
    if (!playing) {
      last.current = 0
      return
    }

    const tick = (now: number) => {
      if (!last.current) last.current = now
      const dt = now - last.current
      last.current = now
      const state = useOpsStore.getState()
      const next = state.t + dt * state.speed
      if (next >= state.tMax) {
        setT(state.tMax)
        setPlaying(false)
        return
      }
      setT(next)
      raf.current = requestAnimationFrame(tick)
    }

    raf.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf.current)
  }, [playing, speed, tMax, setT, setPlaying])
}
