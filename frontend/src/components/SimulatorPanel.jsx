import { useCallback, useEffect, useState } from 'react'
import { ADMIN_KEY_STORAGE, api } from '../api'

const readKey = () => { try { return sessionStorage.getItem(ADMIN_KEY_STORAGE) || '' } catch { return '' } }

export default function SimulatorPanel({ onChange, onClose }) {
  const [status, setStatus] = useState(null)
  const [devices, setDevices] = useState([])
  const [scenarios, setScenarios] = useState([])
  const [scenario, setScenario] = useState('abnormal_temperature')
  const [device, setDevice] = useState('')
  const [duration, setDuration] = useState(20)
  const [key, setKey] = useState(readKey)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [s, d, sc] = await Promise.all([api.simStatus(), api.simDevices(), api.simScenarios()])
      setStatus(s); setDevices(d); setScenarios(sc)
      setDevice((cur) => cur || d[0]?.device_id || '')
    } catch (e) { setMsg({ err: true, text: e.message }) }
  }, [])
  useEffect(() => { refresh() }, [refresh])

  const saveKey = (v) => {
    setKey(v)
    try { v ? sessionStorage.setItem(ADMIN_KEY_STORAGE, v) : sessionStorage.removeItem(ADMIN_KEY_STORAGE) } catch { /* ignore */ }
  }

  const run = async (label, fn) => {
    setBusy(true); setMsg(null)
    try {
      const r = await fn()
      setMsg({ text: `${label}: ${r && r.events !== undefined ? `${r.events} events, ${r.telemetry} telemetry rows` : 'ok'}` })
      await Promise.all([refresh(), onChange()])
    } catch (e) { setMsg({ err: true, text: `${label} failed: ${e.message}` }) } finally { setBusy(false) }
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
          {status.devices} devices · {status.telemetry_rows.toLocaleString()} telemetry rows · live loop:{' '}
          <b>{status.live_running ? 'running' : 'stopped'}</b>
          {status.active_scenarios.length > 0 && <> · active: {status.active_scenarios.map((a) => `${a.scenario} on ${a.device_id} (${a.ticks_done}/${a.total_ticks})`).join(', ')}</>}
        </p>
      )}
      <label>Admin key (only if the server requires one)
        <input type="password" value={key} onChange={(e) => saveKey(e.target.value)} placeholder="X-Admin-Key" autoComplete="off" />
      </label>
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
          <input type="number" min="5" max="120" value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
        </label>
      </div>
      <div className="row">
        <button disabled={busy || !device} onClick={() => run('Inject', () => api.inject(scenario, device, duration))}>Inject scenario</button>
        <button disabled={busy} onClick={() => run('Advance 10 ticks', () => api.tick(10))}>Advance 10 ticks</button>
        <button disabled={busy} onClick={() => run(status?.live_running ? 'Stop' : 'Start', () => (status?.live_running ? api.stop() : api.start()))}>
          {status?.live_running ? 'Stop live loop' : 'Start live loop'}
        </button>
        <button className="danger" disabled={busy} onClick={() => { if (window.confirm('Reset all simulated data and regenerate 24h of history?')) run('Re-seed', api.seed) }}>
          Reset &amp; re-seed
        </button>
      </div>
      {msg && <p className={`small ${msg.err ? 'err' : 'ok'}`}>{msg.text}</p>}
    </div>
  )
}
