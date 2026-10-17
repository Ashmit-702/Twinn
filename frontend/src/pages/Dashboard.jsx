import { useMemo, useState } from 'react'
import { AlertTriangle, Bell, FlaskConical, Layers, Search, ShieldAlert } from 'lucide-react'
import { API_URL, api } from '../api'
import { AnomalyChart, StatusDonut, ThreatsChart } from '../components/Charts'
import SimulatorPanel from '../components/SimulatorPanel'

const fmtTime = (iso) => new Date(iso).toLocaleTimeString([], { hour12: false })
const SEV = { Critical: 'sev-critical', High: 'sev-high', Medium: 'sev-medium', Low: 'sev-low' }
const STATUS_DOT = { Healthy: 'ok', Degraded: 'warn', 'At Risk': 'bad', Offline: 'off' }

function Card({ title, right, children, className = '' }) {
  return (
    <section className={`card ${className}`}>
      {(title || right) && <header className="card-head"><h3>{title}</h3>{right}</header>}
      {children}
    </section>
  )
}

function Stat({ label, icon: Icon, tone, children, sub }) {
  return (
    <section className="card stat">
      <div className="stat-label">{label}</div>
      <div className="stat-body">
        {Icon && <span className={`stat-icon ${tone}`}><Icon size={22} /></span>}
        <span className="stat-value">{children}</span>
      </div>
      <div className="stat-sub">{sub}</div>
    </section>
  )
}

export default function Dashboard({ dash, hours, setHours }) {
  const { data, error, loading, reload } = dash
  const [query, setQuery] = useState('')
  const [showSim, setShowSim] = useState(false)
  const [seeding, setSeeding] = useState(false)
  const [seedErr, setSeedErr] = useState(null)
  const q = query.trim().toLowerCase()

  const twins = useMemo(() => (data?.twins ?? []).filter((t) =>
    !q || [t.twin_code, t.device_id, t.facility, t.status].some((v) => v.toLowerCase().includes(q))), [data, q])
  const events = useMemo(() => (data?.events ?? []).filter((e) =>
    !q || [e.event_type, e.source_device, e.severity].some((v) => v.toLowerCase().includes(q))), [data, q])

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' })
  const s = data?.summary
  const empty = s && s.devices.total === 0

  const initialise = async () => {
    setSeeding(true); setSeedErr(null)
    try { await api.seed(); await reload() } catch (e) { setSeedErr(e.message) } finally { setSeeding(false) }
  }

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Dashboard - Overview</h1>
          <div className="muted">{today}</div>
        </div>
        <div className="top-actions">
          <button className="sim-btn" onClick={() => setShowSim((v) => !v)} aria-expanded={showSim}><FlaskConical size={16} /> Simulator</button>
          <label className="search">
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search" aria-label="Filter tables" />
            <Search size={17} />
          </label>
          <button className="icon-btn" aria-label={`${s?.open_incidents ?? 0} open incidents`}>
            <Bell size={19} />
            {s?.open_incidents > 0 && <b className="badge">{s.open_incidents}</b>}
          </button>
          <div className="avatar sm">AS</div>
        </div>
        {showSim && <SimulatorPanel onChange={reload} onClose={() => setShowSim(false)} />}
      </header>

      {error && (
        <div className="banner" role="alert">
          Can’t reach the API{API_URL ? ` at ${API_URL}` : ''}: {error}
        </div>
      )}
      {loading && !data && <div className="muted">Loading…</div>}

      {empty && (
        <div className="empty-card">
          <h2>No simulation data yet</h2>
          <p>Generate a simulated 24-hour factory history, train the Isolation Forest on the clean baseline and run detection over it.</p>
          <button className="primary" onClick={initialise} disabled={seeding}>{seeding ? 'Initialising…' : 'Initialise simulation'}</button>
          {seedErr && <p className="err small">{seedErr}</p>}
        </div>
      )}

      {data && !empty && (
        <>
          <div className="stats">
            <Stat label="Active Digital Twins" icon={Layers} tone="green" sub="">{s.active_twins}</Stat>
            <Stat label="Devices Monitored"
              sub={<><span className="dot ok" /> Online: {s.devices.online.toLocaleString()} <span className="dot bad" /> Offline: {s.devices.offline}</>}>
              {s.devices.total.toLocaleString()}
            </Stat>
            <Stat label="Active Threats" icon={ShieldAlert} tone="red"
              sub={<><span className="dot bad" /> {s.active_threats.critical} Critical <span className="dot warn" /> {s.active_threats.high} High</>}>
              {s.active_threats.total}
            </Stat>
            <Stat label="Critical Incidents" icon={AlertTriangle} tone="red" sub={<><span className="dot bad" /> Unresolved</>}>
              {s.critical_incidents}
            </Stat>
          </div>

          <div className="grid-2">
            <Card title="Digital Twins" right={<span className="muted small">{twins.length} shown</span>}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>ID</th><th>Facility</th><th>Status</th><th>Security Score</th></tr></thead>
                  <tbody>
                    {twins.map((t) => (
                      <tr key={t.twin_code}>
                        <td>{t.twin_code}</td>
                        <td>{t.device_id}<small>{t.facility}</small></td>
                        <td><span className={`dot ${STATUS_DOT[t.status]}`} /> <span className={`st-${STATUS_DOT[t.status]}`}>{t.status}</span></td>
                        <td>{Math.round(t.security_score)}%</td>
                      </tr>
                    ))}
                    {!twins.length && <tr><td colSpan="4" className="muted">No matches</td></tr>}
                  </tbody>
                </table>
              </div>
            </Card>
            <Card title="Recent Security Events" right={<span className="muted small">{events.length} shown</span>}>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Timestamp</th><th>Event Type</th><th>Severity</th><th>Source Device</th></tr></thead>
                  <tbody>
                    {events.map((e) => (
                      <tr key={e.id}>
                        <td>{fmtTime(e.ts)}</td>
                        <td>{e.event_type}</td>
                        <td className={SEV[e.severity]}>{e.severity}</td>
                        <td>{e.source_device}</td>
                      </tr>
                    ))}
                    {!events.length && <tr><td colSpan="4" className="muted">No events</td></tr>}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>

          <div className="grid-3">
            <Card title="Threats Over Time" right={
              <select className="range" value={hours} onChange={(e) => setHours(Number(e.target.value))} aria-label="Time range">
                <option value={6}>6h</option><option value={12}>12h</option><option value={24}>24h</option>
              </select>}>
              <ThreatsChart data={data.timeline} hours={hours} />
              <div className="legend"><span><i style={{ background: '#2d7cf6' }} />Threats</span><span><i style={{ background: '#ef4b5a' }} />High Severity</span></div>
            </Card>
            <Card title="Anomaly Score Distribution">
              <AnomalyChart data={data.distribution} />
            </Card>
            <Card title="Device Status Overview">
              <StatusDonut status={data.deviceStatus} />
            </Card>
          </div>
        </>
      )}
    </>
  )
}
