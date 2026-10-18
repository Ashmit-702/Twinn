import { PageShell } from '../components/ModeBadge'
import type { DashboardState } from '../useDashboard'
import type { TwinStatus } from '../types'

const DOT: Record<TwinStatus, string> = { Healthy: 'ok', Degraded: 'warn', 'At Risk': 'bad', Offline: 'off' }
const TYPES: Record<string, string> = { cnc: 'CNC Machine', robot: 'Robotic Arm', plc: 'Industrial Controller', temp_sensor: 'Temperature Sensor', pressure_sensor: 'Pressure Sensor' }

export default function DigitalTwin({ dash }: { dash: DashboardState }) {
  const twins = dash.data?.twins ?? []
  return (
    <PageShell title="Digital Twin" subtitle="One simulated twin per factory device, sorted by lowest security score" mode={dash.data?.mode}>
      {dash.error && <div className="banner" role="alert">{dash.error}</div>}
      <section className="card">
        <div className="table-wrap tall">
          <table>
            <thead><tr><th>Twin ID</th><th>Device</th><th>Type</th><th>Facility</th><th>Status</th><th>Security Score</th></tr></thead>
            <tbody>
              {twins.map((t) => (
                <tr key={t.twin_code}>
                  <td>{t.twin_code}</td><td>{t.device_id}</td><td>{TYPES[t.device_type] ?? t.device_type}</td><td>{t.facility}</td>
                  <td><span className={`dot ${DOT[t.status]}`} /> <span className={`st-${DOT[t.status]}`}>{t.status}</span></td>
                  <td>{Math.round(t.security_score)}%</td>
                </tr>
              ))}
              {!twins.length && <tr><td colSpan={6} className="muted">{dash.loading ? 'Loading…' : 'No twins yet'}</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </PageShell>
  )
}
