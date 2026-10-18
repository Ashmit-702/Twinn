import { PageShell } from '../components/ModeBadge'
import type { DashboardState } from '../useDashboard'

export default function Settings({ dash }: { dash: DashboardState }) {
  const mode = dash.data?.mode
  const s = dash.data?.summary
  const yes = (v: boolean | undefined) => (v ? 'Yes' : 'No')
  return (
    <PageShell title="Settings" subtitle="Deployment status (read-only; secrets are never shown)" mode={mode}>
      <section className="card">
        <div className="kv">
          <div><span>Mode</span><b>{mode?.label ?? '…'}</b></div>
          <div><span>PostgreSQL connected</span><b>{yes(mode?.database_connected)}</b></div>
          <div><span>Data persisted</span><b>{yes(mode?.persistent)}</b></div>
          <div><span>Write actions enabled</span><b>{yes(mode?.writes_enabled)}</b></div>
          <div><span>ADMIN_API_KEY configured</span><b>{yes(mode?.admin_key_configured)}</b></div>
          <div><span>Active-threat window</span><b>{s ? `${s.window_minutes} min` : '…'}</b></div>
          <div><span>Explanation method</span><b>occlusion (not SHAP)</b></div>
        </div>
        <p className="muted small">{mode?.message}</p>
        <h4>To enable persistent storage</h4>
        <ol className="small">
          <li>Add a PostgreSQL database (e.g. Neon) and set <code>DATABASE_URL</code> in Vercel → Settings → Environment Variables.</li>
          <li>Set <code>ADMIN_API_KEY</code> (any long random string) to allow write actions.</li>
          <li>Redeploy. Tables and the simulated factory are created automatically, once.</li>
        </ol>
      </section>
    </PageShell>
  )
}
