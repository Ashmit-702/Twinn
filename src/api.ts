import type { EventDetail, Incident, IngestResult, ModeInfo, Overview, ScenarioInfo, SecurityEvent, SimDevice, SimStatus } from './types'

// All requests are same-origin (/api/...). In production Vercel routes /api/* to the Python function;
// in local development Vite proxies /api to the FastAPI dev server (see vite.config.ts).
const ADMIN_KEY_STORAGE = 'twin_admin_key'

export function getAdminKey(): string {
  try { return sessionStorage.getItem(ADMIN_KEY_STORAGE) ?? '' } catch { return '' }
}
export function setAdminKey(value: string): void {
  try {
    if (value) sessionStorage.setItem(ADMIN_KEY_STORAGE, value)
    else sessionStorage.removeItem(ADMIN_KEY_STORAGE)
  } catch { /* storage unavailable (private mode) */ }
}

async function request<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const headers: Record<string, string> = {}
  if (init.body !== undefined) headers['Content-Type'] = 'application/json'
  const key = getAdminKey()
  if (key) headers['X-Admin-Key'] = key

  const res = await fetch(path, {
    method: init.method ?? 'GET',
    headers,
    body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
  })
  if (!res.ok) {
    let detail: unknown
    try { detail = (await res.json() as { detail?: unknown }).detail } catch { /* not JSON */ }
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${res.status} ${res.statusText})`)
  }
  try {
    return (await res.json()) as T
  } catch {
    throw new Error('The server returned an unexpected (non-JSON) response.')
  }
}

export const api = {
  overview: (hours: number) => request<Overview>(`/api/dashboard/overview?hours=${hours}`),
  status: () => request<ModeInfo>('/api/status'),
  events: (limit: number) => request<SecurityEvent[]>(`/api/dashboard/events?limit=${limit}`),
  eventDetail: (id: number) => request<EventDetail>(`/api/dashboard/events/${id}`),
  incidents: (status: 'open' | 'resolved' | 'all') => request<Incident[]>(`/api/incidents?status=${status}`),
  resolveIncident: (id: number) => request<{ id: number; status: string }>(`/api/incidents/${id}/resolve`, { method: 'PATCH' }),
  simStatus: () => request<SimStatus>('/api/simulator/status'),
  simDevices: () => request<SimDevice[]>('/api/simulator/devices'),
  simScenarios: () => request<ScenarioInfo[]>('/api/simulator/scenarios'),
  seed: () => request<IngestResult>('/api/simulator/seed', { method: 'POST', body: { hours: 24 } }),
  tick: (count: number) => request<IngestResult>('/api/simulator/tick', { method: 'POST', body: { count } }),
  inject: (scenario: string, device_id: string, duration_ticks: number) =>
    request<{ id: number }>('/api/simulator/scenarios', { method: 'POST', body: { scenario, device_id, duration_ticks } }),
}
