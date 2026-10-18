import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import type { Overview } from './types'

const POLL_MS = 10_000

export interface DashboardState {
  data: Overview | null
  error: string | null
  loading: boolean
  reload: () => Promise<void>
}

/** Polls one aggregated endpoint (one serverless invocation) and pauses while the tab is hidden. */
export function useDashboard(hours: number): DashboardState {
  const [data, setData] = useState<Overview | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const alive = useRef(true)

  const load = useCallback(async () => {
    try {
      const next = await api.overview(hours)
      if (!alive.current) return
      setData(next)
      setError(null)
    } catch (e) {
      if (alive.current) setError(e instanceof Error ? e.message : 'Failed to reach the API')
    } finally {
      if (alive.current) setLoading(false)
    }
  }, [hours])

  useEffect(() => {
    alive.current = true
    void load()
    const id = setInterval(() => { if (!document.hidden) void load() }, POLL_MS)
    const onVisible = () => { if (!document.hidden) void load() }
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      alive.current = false
      clearInterval(id)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [load])

  return { data, error, loading, reload: load }
}
