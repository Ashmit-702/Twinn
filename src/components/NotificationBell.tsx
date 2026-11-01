import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell } from 'lucide-react'
import { api } from '../api'
import type { Incident, SecurityEvent } from '../types'

const fmt = (iso: string) => new Date(iso).toLocaleString([], { hour12: false })

/** Bell with a dropdown: open incidents and recent High/Critical events. Each item navigates to its detail view. */
export default function NotificationBell({ openIncidents, events }: { openIncidents: number; events: SecurityEvent[] }) {
  const [open, setOpen] = useState(false)
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [error, setError] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)
  const nav = useNavigate()

  useEffect(() => {
    if (!open) return
    let cancelled = false
    api.incidents('open')
      .then((d) => { if (!cancelled) { setIncidents(d.slice(0, 6)); setError(null) } })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)) })
    const onDown = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('keydown', onKey)
    return () => { cancelled = true; document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey) }
  }, [open])

  const go = (to: string) => { setOpen(false); nav(to) }
  const alerts = events.filter((e) => e.severity === 'Critical' || e.severity === 'High').slice(0, 6)

  return (
    <div className="notif" ref={ref}>
      <button className="icon-btn" onClick={() => setOpen((v) => !v)} aria-haspopup="true" aria-expanded={open}
        aria-label={`Notifications: ${openIncidents} open incidents`}>
        <Bell size={19} />
        {openIncidents > 0 && <b className="badge">{openIncidents}</b>}
      </button>
      {open && (
        <div className="notif-panel" role="menu" aria-label="Notifications">
          <div className="notif-title">Open incidents</div>
          {error && <div className="err small">{error}</div>}
          {!error && !incidents.length && <div className="muted small notif-empty">No open incidents</div>}
          {incidents.map((i) => (
            <button key={i.id} className="notif-item" role="menuitem" onClick={() => go(`/incidents?incident=${i.id}`)}>
              <span className={`sev-${i.severity.toLowerCase()}`}>{i.severity}</span> {i.title}
              <small>{i.device_id} · {fmt(i.last_event_at)} · {i.event_count} events</small>
            </button>
          ))}
          <div className="notif-title">Recent high-severity events</div>
          {!alerts.length && <div className="muted small notif-empty">No recent high-severity events</div>}
          {alerts.map((e) => (
            <button key={e.id} className="notif-item" role="menuitem" onClick={() => go(`/xai-analysis?event=${e.id}`)}>
              <span className={`sev-${e.severity.toLowerCase()}`}>{e.severity}</span> {e.event_type}
              <small>{e.source_device} · {fmt(e.ts)}</small>
            </button>
          ))}
          <button className="link notif-all" onClick={() => go('/incidents')}>View all incidents</button>
        </div>
      )}
    </div>
  )
}
