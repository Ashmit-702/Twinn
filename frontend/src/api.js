// API base URL comes from the environment. Empty = same origin (dev server proxies /api to FastAPI).
export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export const ADMIN_KEY_STORAGE = 'twin_admin_key'

async function request(path, { method = 'GET', body } = {}) {
  if (import.meta.env.PROD && !API_URL) {
    throw new Error('VITE_API_URL is not configured for this deployment.')
  }
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  try {
    const key = sessionStorage.getItem(ADMIN_KEY_STORAGE)
    if (key) headers['X-Admin-Key'] = key
  } catch { /* storage unavailable */ }
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    let detail
    try { detail = (await res.json()).detail } catch { /* not JSON */ }
    throw new Error(typeof detail === 'string' ? detail : `${res.status} ${res.statusText}`)
  }
  return res.json()
}

export const api = {
  summary: () => request('/api/dashboard/summary'),
  twins: () => request('/api/dashboard/twins?limit=100'),
  events: () => request('/api/dashboard/events?limit=50'),
  timeline: (hours) => request(`/api/dashboard/threats-timeline?hours=${hours}`),
  distribution: () => request('/api/dashboard/anomaly-distribution'),
  deviceStatus: () => request('/api/dashboard/device-status'),
  simStatus: () => request('/api/simulator/status'),
  simDevices: () => request('/api/simulator/devices'),
  simScenarios: () => request('/api/simulator/scenarios'),
  seed: () => request('/api/simulator/seed', { method: 'POST', body: { hours: 24 } }),
  tick: (count) => request('/api/simulator/tick', { method: 'POST', body: { count } }),
  inject: (scenario, device_id, duration_ticks) =>
    request('/api/simulator/scenarios', { method: 'POST', body: { scenario, device_id, duration_ticks } }),
  start: () => request('/api/simulator/start', { method: 'POST' }),
  stop: () => request('/api/simulator/stop', { method: 'POST' }),
}
