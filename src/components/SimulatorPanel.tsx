import { useCallback, useEffect, useState } from 'react'
import { api } from '../api'
import type { IngestResult, ScenarioInfo, SimDevice, SimStatus } from '../types'
import AdminKeyInput from './AdminKeyInput'

interface Props {
  onChange: () => Promise<void>
  onClose: () => void
  live: boolean
  onLiveChange: (live: boolean) => void
  liveError: string | null
}

interface Msg { err?: boolean; text: string }

export default function SimulatorPanel({ onChange, onClose, live, onLiveChange, liveError }: Props) {
  const [status, setStatus] = useState<SimStatus | null>(null)
  const [devices, setDevices] = useState<SimDevice[]>([])
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([])
  const [scenario, setScenario] = useState('abnormal_temperature')
  const [device, setDevice] = useState('')
  const [duration, setDuration] = useState(20)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<Msg | null>(null)

  const refresh = useCallback(async () => {
    try {
      const [s, d, sc] = await Promise.all([api.simStatus(), api.simDevices(), api.simScenarios()])
      setStatus(s); setDevices(d); setScenarios(sc)
      setDevice((cur) => cur || d[0]?.device_id || '')
    } catch (e) { setMsg({ err: true, text: e instanceof Error ? e.message : String(e) }) }
  }, [])
  useEffect(() => { void refresh() }, [refresh])

  const run = async (label: string, fn: () => Promise<IngestResult | { id: number }>) => {
    setBusy(true); setMsg(null)
    try {
      const r = await fn()
      setMsg({ text: `${label}: ${'events' in r ? `${r.events} events, ${r.telemetry} telemetry rows` : 'ok'}` })
      await Promise.all([refresh(), onChange()])
    } catch (e) {
      setMsg({ err: true, text: `${label} failed: ${e instanceof Error ? e.message : String(e)}` })
    } finally { setBusy(false) }
  }

  return (
    <div className="sim-panel" role="dialog" aria-label="Simulator controls">
      <div className="sim-head">
        <strong>Factory simulator</strong>
        <button className="link" onClick={onClose}>Close</button>
      </div>
      <p className="muted small">All devices and attacks are simulated. Scenario data flows through the real detection pipeline.</p>
      {status && (
        <p className="small">
          {status.devices} devices · {status.telemetry_rows.toLocaleString()} telemetry rows · model: <b>{status.model_ready ? 'stored in database' : 'not trained'}</b>
          {status.active_scenarios.length > 0 && <> · active: {status.active_scenarios.map((a) => `${a.scenario} on ${a.device_id} (${a.ticks_done}/${a.total_ticks})`).join(', ')}</>}
        </p>
      )}
      <AdminKeyInput hint="Admin key (required to change data in production)" />
      <div className="row sel">
        <label>Scenario
          <select value={scenario} onChange={(e) => setScenario(e.target.value)}>
            {scenarios.map((s) => <option key={s.id} value={s.id} title={s.description}>{s.id.replace(/_/g, ' ')}</option>)}
          </select>
        </label>
        <label>Device
          <select value={device} onChange={(e) => setDevice(e.target.value)}>
            {devices.map((d) => <option key={d.device_id} value={d.device_id}>{d.device_id} ({d.label})</option>)}
          </select>
        </label>
        <label>Ticks
          <input type="number" min={5} max={120} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
        </label>
      </div>
      <div className="row">
        <button disabled={busy || !device} onClick={() => run('Inject', () => api.inject(scenario, device, duration))}>Inject scenario</button>
        <button disabled={busy} onClick={() => run('Advance 10 ticks', () => api.tick(10))}>Advance 10 ticks</button>
        <button onClick={() => onLiveChange(!live)} aria-pressed={live}>{live ? 'Stop live mode' : 'Start live mode'}</button>
        <button className="danger" disabled={busy} onClick={() => { if (window.confirm('Reset all simulated data and regenerate 24h of history?')) void run('Re-seed', api.seed) }}>
          Reset &amp; re-seed
        </button>
      </div>
      <p className="muted small">Live mode advances the simulation by one tick every 5 s from this browser tab (the server runs no background jobs).</p>
      {liveError && <p className="small err">Live mode stopped: {liveError}</p>}
      {msg && <p className={`small ${msg.err ? 'err' : 'ok'}`}>{msg.text}</p>}
    </div>
  )
}
