import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'

const POLL_MS = 5000

export function useDashboard(hours) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const alive = useRef(true)

  const load = useCallback(async () => {
    try {
      const [summary, twins, events, timeline, distribution, deviceStatus] = await Promise.all([
        api.summary(), api.twins(), api.events(), api.timeline(hours), api.distribution(), api.deviceStatus(),
      ])
      if (!alive.current) return
      setData({ summary, twins, events, timeline, distribution, deviceStatus })
      setError(null)
    } catch (e) {
      if (alive.current) setError(e.message || 'Failed to reach the API')
    } finally {
      if (alive.current) setLoading(false)
    }
  }, [hours])

  useEffect(() => {
    alive.current = true
    load()
    const id = setInterval(load, POLL_MS)
    return () => { alive.current = false; clearInterval(id) }
  }, [load])

  return { data, error, loading, reload: load }
}
