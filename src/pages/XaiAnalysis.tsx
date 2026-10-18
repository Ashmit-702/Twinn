import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api } from '../api'
import { PageShell } from '../components/ModeBadge'
import { useApi } from '../useApi'
import type { ModeInfo, Severity } from '../types'

const SEV: Record<Severity, string> = { Critical: 'sev-critical', High: 'sev-high', Medium: 'sev-medium', Low: 'sev-low' }
const LABEL: Record<string, string> = {
  z_temperature: 'Temperature (σ from normal)', z_pressure: 'Pressure (σ)', z_vibration: 'Vibration (σ)', z_cpu_load: 'CPU load (σ)',
  z_net_in_pps: 'Inbound packets/s (σ)', z_net_out_pps: 'Outbound packets/s (σ)', z_failed_logins: 'Failed logins (σ)', z_cmd_rate: 'Command rate (σ)',
  d_temperature: 'Temperature change', d_pressure: 'Pressure change', rstd_temperature: 'Temperature variability', rstd_pressure: 'Pressure variability',
}

export default function XaiAnalysis({ mode }: { mode?: ModeInfo }) {
  const [params, setParams] = useSearchParams()
  const list = useApi(() => api.events(100), 'xai-list')
  const [selected, setSelected] = useState<number | null>(params.get('event') ? Number(params.get('event')) : null)
  useEffect(() => { if (selected === null && list.data?.length) setSelected(list.data[0].id) }, [list.data, selected])
  const detail = useApi(() => (selected === null ? Promise.resolve(null) : api.eventDetail(selected)), selected)
  const d = detail.data
  const max = Math.max(1e-9, ...(d?.explanation ?? []).map((x) => x.contribution))

  return (
    <PageShell title="XAI Analysis" subtitle="Why was an event flagged? Per-event feature attribution from the Isolation Forest" mode={mode}>
      {(list.error || detail.error) && <div className="banner" role="alert">{list.error ?? detail.error}</div>}
      <div className="xai">
        <section className="card xai-list">
          <h3>Recent events</h3>
          <div className="table-wrap tall">
            <table><tbody>
              {(list.data ?? []).map((e) => (
                <tr key={e.id} className={`clickable${e.id === selected ? ' sel' : ''}`} onClick={() => { setSelected(e.id); setParams({ event: String(e.id) }) }}>
                  <td>{new Date(e.ts).toLocaleTimeString([], { hour12: false })}</td><td>{e.event_type}<small>{e.source_device}</small></td><td className={SEV[e.severity]}>{e.severity}</td>
                </tr>
              ))}
              {!(list.data ?? []).length && <tr><td className="muted">{list.loading ? 'Loading…' : 'No events'}</td></tr>}
            </tbody></table>
          </div>
        </section>
        <section className="card">
          {!d && <p className="muted">{detail.loading ? 'Loading…' : 'Select an event.'}</p>}
          {d && (
            <>
              <h3>{d.event_type} <span className={SEV[d.severity]}>· {d.severity}</span></h3>
              <p className="muted small">{d.device_id} ({d.facility}) · {new Date(d.ts).toLocaleString([], { hour12: false })}</p>
              <div className="kv">
                <div><span>Anomaly score</span><b>{Math.round(d.anomaly_score)} / 100</b></div>
                <div><span>Risk score</span><b>{Math.round(d.risk_score)} / 100</b></div>
                <div><span>Detected by</span><b>{d.source}</b></div>
                <div><span>IDS rules fired</span><b>{d.rule_ids.join(', ') || 'none'}</b></div>
              </div>
              <h4>Top features pushing toward “anomalous”</h4>
              {d.explanation.length === 0 && <p className="muted small">No single feature stood out (the rule fired without a clear Isolation Forest driver).</p>}
              {d.explanation.map((x) => (
                <div className="bar-row" key={x.feature}>
                  <span>{LABEL[x.feature] ?? x.feature}</span>
                  <div className="bar"><div style={{ width: `${Math.max(3, (100 * x.contribution) / max)}%` }} /></div>
                  <b>{x.contribution.toFixed(1)}</b>
                </div>
              ))}
              <p className="muted small">
                Method: <b>{d.explain_method ?? 'n/a'}</b>. Occlusion attribution resets one feature to its normal value and measures how much the
                anomaly score falls. It is a single-feature counterfactual — <b>not SHAP</b> — and can under-credit anomalies that need several features together.
              </p>
              <h4>Telemetry at detection time</h4>
              <div className="kv small-kv">{Object.entries(d.features).map(([k, v]) => <div key={k}><span>{k}</span><b>{v}</b></div>)}</div>
            </>
          )}
        </section>
      </div>
    </PageShell>
  )
}
