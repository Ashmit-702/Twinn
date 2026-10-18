import type { ReactNode } from 'react'
import type { ModeInfo } from '../types'

export function ModeBadge({ mode }: { mode?: ModeInfo }) {
  if (!mode) return null
  return (
    <span className={`mode-badge ${mode.database_connected ? 'db' : 'demo'}`} title={mode.message} role="status">
      <i /> {mode.label}
    </span>
  )
}

export function ModeNotice({ mode }: { mode?: ModeInfo }) {
  if (!mode || mode.database_connected) return null
  return (
    <div className="notice" role="note">
      <b>DEMO MODE</b>
      <span>{mode.message}</span>
    </div>
  )
}

export function PageShell({ title, subtitle, mode, children }: { title: string; subtitle?: string; mode?: ModeInfo; children: ReactNode }) {
  return (
    <>
      <header className="topbar">
        <div>
          <h1>{title}</h1>
          {subtitle && <div className="muted">{subtitle}</div>}
        </div>
        <div className="top-actions"><ModeBadge mode={mode} /></div>
      </header>
      <ModeNotice mode={mode} />
      {children}
    </>
  )
}
