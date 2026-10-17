import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, LabelList, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

const AXIS = { stroke: '#8693b3', fontSize: 12, tickLine: false, axisLine: { stroke: '#1f2d52' } }
const hh = (iso) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })

function Tip({ active, payload, label, fmt }) {
  if (!active || !payload?.length) return null
  return (
    <div className="tip">
      <div>{fmt ? fmt(label) : label}</div>
      {payload.map((p) => (
        <div key={p.dataKey}><i style={{ background: p.color || p.stroke }} />{p.name}: <b>{p.value}</b></div>
      ))}
    </div>
  )
}

export function ThreatsChart({ data, hours }) {
  const rows = data.map((d) => ({ ...d, label: hh(d.ts) }))
  const step = hours <= 12 ? 1 : 3
  return (
    <ResponsiveContainer width="100%" height={210}>
      <AreaChart data={rows} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id="gBlue" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#2d7cf6" stopOpacity=".55" /><stop offset="1" stopColor="#2d7cf6" stopOpacity="0" /></linearGradient>
          <linearGradient id="gRed" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ef4b5a" stopOpacity=".55" /><stop offset="1" stopColor="#ef4b5a" stopOpacity="0" /></linearGradient>
        </defs>
        <CartesianGrid stroke="#1a2745" vertical={false} />
        <XAxis dataKey="label" interval={step - 1} {...AXIS} />
        <YAxis allowDecimals={false} {...AXIS} />
        <Tooltip content={<Tip />} />
        <Area type="monotone" dataKey="threats" name="Threats" stroke="#2d7cf6" strokeWidth={2} fill="url(#gBlue)" />
        <Area type="monotone" dataKey="high_severity" name="High Severity" stroke="#ef4b5a" strokeWidth={2} fill="url(#gRed)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function AnomalyChart({ data }) {
  return (
    <ResponsiveContainer width="100%" height={210}>
      <BarChart data={data} margin={{ top: 18, right: 8, left: -14, bottom: 14 }}>
        <CartesianGrid stroke="#1a2745" vertical={false} />
        <XAxis dataKey="bin" {...AXIS} label={{ value: 'Anomaly Score', position: 'insideBottom', offset: -8, fill: '#8693b3', fontSize: 12 }} />
        <YAxis allowDecimals={false} {...AXIS} label={{ value: 'Devices', angle: -90, position: 'insideLeft', offset: 18, fill: '#8693b3', fontSize: 12 }} />
        <Tooltip cursor={{ fill: 'rgba(45,124,246,.08)' }}
          content={<Tip fmt={(b) => `Score ${b}–${b + 10}`} />} />
        <Bar dataKey="devices" name="Devices" fill="#2d7cf6" radius={[2, 2, 0, 0]}>
          <LabelList dataKey="devices" position="top" fill="#c9d3ea" fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

const DONUT = [
  { key: 'online', label: 'Online', color: '#2d7cf6' },
  { key: 'offline', label: 'Offline', color: '#ef4b5a' },
  { key: 'alerting', label: 'Alerting', color: '#f0b429' },
]

export function StatusDonut({ status }) {
  const slices = DONUT.map((d) => ({ ...d, value: status[d.key] })).filter((d) => d.value > 0)
  return (
    <div>
      <ResponsiveContainer width="100%" height={180}>
        <PieChart>
          <Pie data={slices} dataKey="value" nameKey="label" innerRadius={52} outerRadius={80} stroke="none" paddingAngle={slices.length > 1 ? 1 : 0}>
            {slices.map((s) => <Cell key={s.key} fill={s.color} />)}
          </Pie>
          <Tooltip content={<Tip />} />
        </PieChart>
      </ResponsiveContainer>
      <div className="legend">
        {DONUT.map((d) => (
          <span key={d.key}><i style={{ background: d.color }} />{d.label}: {status[`${d.key}_pct`]}%</span>
        ))}
      </div>
    </div>
  )
}
