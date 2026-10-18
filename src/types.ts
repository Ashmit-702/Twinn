export type Severity = 'Critical' | 'High' | 'Medium' | 'Low'
export type TwinStatus = 'Healthy' | 'Degraded' | 'At Risk' | 'Offline'

export interface Summary {
  active_twins: number
  devices: { total: number; online: number; offline: number }
  active_threats: { total: number; critical: number; high: number }
  critical_incidents: number
  open_incidents: number
  window_minutes: number
  server_time: string
}
export interface Twin {
  twin_code: string
  device_id: string
  device_type: string
  facility: string
  status: TwinStatus
  security_score: number
}
export interface SecurityEvent {
  id: number
  ts: string
  event_type: string
  severity: Severity
  source_device: string
  threat_class: string
  risk_score: number
  anomaly_score: number
  source: string
  rule_ids: string[]
}
export interface EventDetail {
  id: number; ts: string; event_type: string; severity: Severity; threat_class: string; source: string
  anomaly_score: number; risk_score: number; rule_ids: string[]; device_id: string; device_type: string
  facility: string; features: Record<string, number>
  explanation: { feature: string; contribution: number }[]; explain_method: string | null
}
export interface Incident {
  id: number; title: string; device_id: string; threat_class: string; severity: Severity
  status: 'open' | 'resolved'; opened_at: string; last_event_at: string; event_count: number
}
export interface TimelinePoint { ts: string; threats: number; high_severity: number }
export interface DistributionBin { bin: number; devices: number }
export interface DeviceStatus {
  total: number; online: number; offline: number; alerting: number
  online_pct: number; offline_pct: number; alerting_pct: number
}
export interface ModeInfo {
  mode: 'demo' | 'database'
  label: 'DEMO MODE' | 'DATABASE CONNECTED'
  database_connected: boolean
  persistent: boolean
  writes_enabled: boolean
  reason: string | null
  admin_key_configured: boolean
  message: string
}
export interface Overview {
  summary: Summary
  twins: Twin[]
  events: SecurityEvent[]
  timeline: TimelinePoint[]
  distribution: DistributionBin[]
  device_status: DeviceStatus
  mode: ModeInfo
}
export interface ActiveScenario { scenario: string; device_id: string; ticks_done: number; total_ticks: number }
export interface SimStatus {
  devices: number
  telemetry_rows: number
  model_ready: boolean
  active_scenarios: ActiveScenario[]
}
export interface SimDevice { device_id: string; device_type: string; label: string; facility: string; is_online: boolean }
export interface ScenarioInfo { id: string; description: string }
export interface IngestResult { telemetry: number; events: number; incidents_opened: number; ticks?: number }
