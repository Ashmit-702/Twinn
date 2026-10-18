import type { LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import {
  AlertTriangle, BookOpen, Brain, ChevronDown, LayoutGrid, Layers, Search, Settings, ShieldCheck, TrendingUp,
} from 'lucide-react'

interface NavEntry { slug: string; label: string; icon: LucideIcon; alert?: boolean; ready?: boolean }

const NAV: NavEntry[] = [
  { slug: '', label: 'Dashboard', icon: LayoutGrid },
  { ready: true, slug: 'digital-twin', label: 'Digital Twin', icon: Layers },
  { ready: true, slug: 'threat-detection', label: 'Threat Detection', icon: Search },
  { ready: true, slug: 'incidents', label: 'Incidents', icon: AlertTriangle, alert: true },
  { ready: true, slug: 'xai-analysis', label: 'XAI Analysis', icon: Brain },
  { slug: 'incident-response', label: 'Incident Response', icon: ShieldCheck },
  { slug: 'analytics', label: 'Analytics', icon: TrendingUp },
  { slug: 'audit-logs', label: 'Audit Logs', icon: BookOpen },
  { ready: true, slug: 'settings', label: 'Settings', icon: Settings },
]

function Logo() {
  return (
    <div className="logo">
      <svg width="44" height="44" viewBox="0 0 44 44" aria-hidden="true">
        <defs>
          <linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#35d0ff" /><stop offset="1" stopColor="#2563eb" />
          </linearGradient>
        </defs>
        <path d="M5 8h30v8H25v20h-8V16H5z" fill="url(#lg)" />
        <path d="M29 22l8-4v10c0 5-4 8-8 10-1-1-1-1-1-2V22z" fill="#1e5fd8" opacity=".85" />
      </svg>
      <div>
        <div className="logo-word">TWIN</div>
        <div className="logo-sub">Smart Factory Security</div>
      </div>
    </div>
  )
}

export default function Sidebar({ openIncidents = 0 }: { openIncidents?: number }) {
  return (
    <aside className="sidebar">
      <Logo />
      {/* Static placeholder identity: there is no authentication yet. */}
      <div className="user">
        <div className="avatar">AS</div>
        <div className="user-text">
          <strong>A. Sharma</strong>
          <span>Cybersecurity Analyst</span>
        </div>
        <ChevronDown size={16} />
      </div>
      <nav>
        {NAV.map(({ slug, label, icon: Icon, alert, ready }) => (
          <NavLink key={label} to={ready ? `/${slug}` : slug ? `/soon/${slug}` : '/'} end className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            {({ isActive }) => (
              <>
                <Icon size={20} strokeWidth={1.7} />
                <span>{label}</span>
                {isActive && !slug && <em className="tag tag-blue">Active</em>}
                {alert && openIncidents > 0 && <em className="tag tag-plain">Alert</em>}
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </aside>
  )
}
