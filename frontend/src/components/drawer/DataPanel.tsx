import { useRef, useState } from 'react'
import { Upload, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import { useOpsStore } from '@/hooks/useOpsStore'

interface Props {
  onDataChanged: () => Promise<void>
}

export function DataPanel({ onDataChanged }: Props) {
  const setError = useOpsStore((s) => s.setError)
  const setLoading = useOpsStore((s) => s.setLoading)
  const totalHint = useOpsStore((s) => s.drones)
  const [message, setMessage] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const onUpload = async (file: File) => {
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const res = await api.upload(file)
      setMessage(res.message)
      await onDataChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const reloadDemo = async () => {
    setLoading(true)
    setError(null)
    setMessage(null)
    try {
      const res = await api.reloadDemo()
      setMessage(res.message)
      await onDataChanged()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4 p-4">
      <div>
        <h3 className="text-sm font-semibold text-ops-text">Telemetry Data</h3>
        <p className="mt-1 text-xs text-ops-muted">
          CSV columns: aircraft_id, timestamp, latitude, longitude, altitude, heading
        </p>
      </div>

      <div
        className="flex cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-ops-border bg-ops-bg px-4 py-8 text-center transition-colors hover:border-ops-accent/50"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault()
          const f = e.dataTransfer.files?.[0]
          if (f) void onUpload(f)
        }}
      >
        <Upload className="mb-2 h-6 w-6 text-ops-accent" />
        <p className="text-sm text-ops-text">Drop CSV or click to select</p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const f = e.target.files?.[0]
            if (f) void onUpload(f)
          }}
        />
      </div>

      <Button variant="outline" className="w-full" onClick={reloadDemo}>
        <RefreshCw className="h-4 w-4" />
        Reload demo dataset
      </Button>

      <div className="rounded-md border border-ops-border bg-ops-bg p-3 font-mono text-xs text-ops-muted">
        <div>{totalHint.length} aircraft in store</div>
        {message && <div className="mt-1 text-ops-safe">{message}</div>}
      </div>
    </div>
  )
}
