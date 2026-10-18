import { useCallback, useEffect, useState } from 'react'

/** Minimal fetch hook for the secondary pages (loads on mount and when `key` changes). */
export function useApi<T>(fn: () => Promise<T>, key: unknown): { data: T | null; error: string | null; loading: boolean; reload: () => void } {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [tick, setTick] = useState(0)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const stable = useCallback(fn, [key])
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    stable().then((d) => { if (!cancelled) { setData(d); setError(null) } })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [stable, tick])
  return { data, error, loading, reload: () => setTick((t) => t + 1) }
}
