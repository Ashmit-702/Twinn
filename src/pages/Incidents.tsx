import { useState } from 'react'
import { api } from '../api'
import AdminKeyInput from '../components/AdminKeyInput'
import { PageShell } from '../components/ModeBadge'
import { useApi } from '../useApi'
import type { Incident, ModeInfo, Severity } from '../types'

const SEV: Record<Severity, string> = { Critical: 'sev-critical', High: 'sev-high', Medium: 'sev-medium', Low: 'sev-low' }

export default function Incidents({ mode }: { mode?: ModeInfo }) {
  const [filter, setFilter] = useState<'open' | 'resolved' | 'all'>('open')
  const { data, error, loading, reload } = useApi<Incident[]>(() => api.incidents(filter), filter)
  const [msg, setMsg] = useState<string | null>(null)
  const canResolve = mode?.writes_enabled ?? false

  const resolve = async (id: number) => {
    setMsg(null)
    try { await api.resolveIncident(id); reload() } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
  }
  return (
    <PageShell title="Incidents" subtitle="Critical detections are grouped into one incident per device and threat class; they auto-resolve after 60 minutes without a new Critical event" mode={mode}>
      {error && <div className="banner" role="alert">{error}</div>}
      <section className="card">
        <div className="filters">
          <select value={filter} onChange={(e) => setFilter(e.target.value as 'open' | 'resolved' | 'all')} aria-label="Status filter">
            <option value="open">Open</option><option value="resolved">Resolved</option><option value="all">All</option>
          </select>
          {canResolve && <div className="inline-key"><AdminKeyInput hint="Admin key (needed to resolve)" /></div>}
          {!canResolve && <span className="muted small">Resolving incidents needs PostgreSQL (disabled in DEMO MODE).</span>}
        </div>
        {msg && <p className="err small">{msg}</p>}
        <div className="table-wrap tall">
          <table>
            <thead><tr><th>#</th><th>Incident</th><th>Device</th><th>Severity</th><th>Status</th><th>Opened</th><th>Events</th><th /></tr></thead>
            <tbody>
              {(data ?? []).map((i) => (
                <tr key={i.id}>
                  <td>{i.id}</td><td>{i.title}</td><td>{i.device_id}</td><td className={SEV[i.severity]}>{i.severity}</td>
                  <td><span className={`dot ${i.status === 'open' ? 'bad' : 'ok'}`} /> {i.status}</td>
                  <td>{new Date(i.opened_at).toLocaleString([], { hour12: false })}</td><td>{i.event_count}</td>
                  <td>{i.status === 'open' && <button className="mini" disabled={!canResolve} onClick={() => resolve(i.id)}>Resolve</button>}</td>
                </tr>
              ))}
              {!(data ?? []).length && <tr><td colSpan={8} className="muted">{loading ? 'Loading…' : 'No incidents'}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </PageShell>
  )
}
