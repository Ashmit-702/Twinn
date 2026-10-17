import { useState } from 'react'
import { Route, Routes } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import ComingSoon from './pages/ComingSoon'
import { useDashboard } from './useDashboard'

export default function App() {
  const [hours, setHours] = useState(24)
  const dash = useDashboard(hours)
  return (
    <div className="shell">
      <Sidebar openIncidents={dash.data?.summary.open_incidents ?? 0} />
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard dash={dash} hours={hours} setHours={setHours} />} />
          <Route path="/soon/:slug" element={<ComingSoon />} />
          <Route path="*" element={<ComingSoon />} />
        </Routes>
      </main>
    </div>
  )
}
