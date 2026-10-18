import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { PageShell } from '../components/ModeBadge'
import { useApi } from '../useApi'
import type { ModeInfo, Severity } from '../types'

const SEV: Record<Severity, string> = { Critical: 'sev-critical', High: 'sev-high', Medium: 'sev-medium', Low: 'sev-low' }
const SRC: Record<string, string> = { ids: 'IDS rules', ml: 'Isolation Forest', 'ids+ml': 'IDS + Isolation Forest' }

export default function ThreatDetection({ mode }: { mode?: ModeInfo }) {
  const { data, error, loading } = useApi(() => api.events(200), 'events')
  const [sev, setSev] = useState<'all' | Severity>('all')
  const [q, setQ] = useState('')
  const nav = useNavigate()
  const rows = useMemo(() => (data ?? []).filter((e) => (sev === 'all' || e.severity === sev) &&
    (!q || `${e.event_type} ${e.source_device}`.toLowerCase().includes(q.toLowerCase()))), [data, sev, q])
  return (
    <PageShell title="Threat Detection" subtitle="Events from the rule-based IDS and the Isolation Forest (latest 200). Click a row for its explanation." mode={mode}>
      {error && <div className="banner" role="alert">{error}</div>}
      <section className="card">
        <div className="filters">
          <select value={sev} onChange={(e) => setSev(e.target.value as 'all' | Severity)} aria-label="Severity filter">
            <option value="all">All severities</option><option>Critical</option><option>High</option><option>Medium</option><option>Low</option>
          </select>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by type or device" aria-label="Filter events" />
          <span className="muted small">{rows.length} shown</span>
        </div>
        <div className="table-wrap tall">
          <table>
            <thead><tr><th>Time</th><th>Event Type</th><th>Severity</th><th>Device</th><th>Detected by</th><th>Rules</th><th>Anomaly</th><th>Risk</th></tr></thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id} className="clickable" onClick={() => nav(`/xai-analysis?event=${e.id}`)}>
                  <td>{new Date(e.ts).toLocaleString([], { hour12: false })}</td><td>{e.event_type}</td>
                  <td className={SEV[e.severity]}>{e.severity}</td><td>{e.source_device}</td><td>{SRC[e.source] ?? e.source}</td>
                  <td>{e.rule_ids.join(', ') || '—'}</td><td>{Math.round(e.anomaly_score)}</td><td>{Math.round(e.risk_score)}</td>
                </tr>
              ))}
              {!rows.length && <tr><td colSpan={8} className="muted">{loading ? 'Loading…' : 'No events match'}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </PageShell>
  )
}
