import { useMemo } from 'react'
import { api } from '../api'
import { AnomalyChart, ThreatsChart } from '../components/Charts'
import { PageShell } from '../components/ModeBadge'
import { useApi } from '../useApi'
import type { DashboardState } from '../useDashboard'
import type { Severity } from '../types'

const SEVS: Severity[] = ['Critical', 'High', 'Medium', 'Low']
const SEV: Record<Severity, string> = { Critical: 'sev-critical', High: 'sev-high', Medium: 'sev-medium', Low: 'sev-low' }

function top(rows: string[], n = 6): [string, number][] {
  const m = new Map<string, number>()
  rows.forEach((r) => m.set(r, (m.get(r) ?? 0) + 1))
  return [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n)
}

/** Basic analytics computed from data already in the database (latest 200 events + all incidents + dashboard series). */
export default function Analytics({ dash }: { dash: DashboardState }) {
  const events = useApi(() => api.events(200), 'analytics-events')
  const incidents = useApi(() => api.incidents('all'), 'analytics-incidents')
  const ev = events.data ?? []
  const inc = incidents.data ?? []
  const bySev = useMemo(() => SEVS.map((s) => [s, ev.filter((e) => e.severity === s).length] as const), [ev])
  const types = useMemo(() => top(ev.map((e) => e.event_type)), [ev])
  const devices = useMemo(() => top(ev.map((e) => e.source_device)), [ev])
  const classes = useMemo(() => top(ev.map((e) => e.threat_class)), [ev])
  const open = inc.filter((i) => i.status === 'open').length
  const err = events.error ?? incidents.error ?? dash.error
  const d = dash.data

  const list = (rows: [string, number][]) => (
    <table><tbody>
      {rows.map(([k, v]) => <tr key={k}><td>{k.replace(/_/g, ' ')}</td><td style={{ textAlign: 'right' }}><b>{v}</b></td></tr>)}
      {!rows.length && <tr><td className="muted">{events.loading ? 'Loading…' : 'No data'}</td></tr>}
    </tbody></table>
  )

  return (
    <PageShell title="Analytics" subtitle="Summary of detections and incidents (latest 200 events, all incidents)" mode={d?.mode}>
      {err && <div className="banner" role="alert">{err}</div>}
      <div className="kv">
        <div><span>Events analysed</span><b>{ev.length}</b></div>
        <div><span>Incidents (total / open)</span><b>{inc.length} / {open}</b></div>
        {bySev.map(([s, n]) => <div key={s}><span>{s} events</span><b className={SEV[s]}>{n}</b></div>)}
      </div>
      <div className="grid-2">
        <section className="card"><header className="card-head"><h3>Top event types</h3></header>{list(types)}</section>
        <section className="card"><header className="card-head"><h3>Threat classes</h3></header>{list(classes)}</section>
      </div>
      <div className="grid-2">
        <section className="card"><header className="card-head"><h3>Most affected devices</h3></header>{list(devices)}</section>
        <section className="card"><header className="card-head"><h3>Anomaly score distribution</h3></header>
          {d ? <AnomalyChart data={d.distribution} /> : <p className="muted">Loading…</p>}
        </section>
      </div>
      <section className="card"><header className="card-head"><h3>Threats over the last 24 hours</h3></header>
        {d ? <ThreatsChart data={d.timeline} hours={24} /> : <p className="muted">Loading…</p>}
      </section>
    </PageShell>
  )
}
