import { useCallback, useEffect, useRef } from 'react'
import { useOpsStore } from '@/hooks/useOpsStore'

/**
 * WebSocket client for /ws/telemetry.
 * MVP uses local replay clock; this hook keeps the stream path ready for live.
 */
export function useTelemetrySocket(enabled = true) {
  const wsRef = useRef<WebSocket | null>(null)
  const setWsConnected = useOpsStore((s) => s.setWsConnected)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const url = `${proto}://${window.location.host}/ws/telemetry`
    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setWsConnected(true)
      ws.send(
        JSON.stringify({
          type: 'subscribe',
          mode: 'replay',
          playing: false,
          speed: 1,
        }),
      )
    }

    ws.onclose = () => {
      setWsConnected(false)
    }

    ws.onerror = () => {
      setWsConnected(false)
    }

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string)
        // Ready for live: when mode===live, could setT from msg.t
        if (msg.type === 'tick' && msg.mode === 'live' && msg.t) {
          useOpsStore.getState().setT(new Date(msg.t).getTime())
        }
      } catch {
        /* ignore */
      }
    }
  }, [setWsConnected])

  const disconnect = useCallback(() => {
    wsRef.current?.close()
    wsRef.current = null
    setWsConnected(false)
  }, [setWsConnected])

  useEffect(() => {
    if (!enabled) return
    connect()
    return () => disconnect()
  }, [enabled, connect, disconnect])

  return { connect, disconnect, wsRef }
}
