import { useState } from 'react'
import { getAdminKey, setAdminKey } from '../api'

/** The admin key is kept in sessionStorage only (never bundled) and sent as the X-Admin-Key header. */
export default function AdminKeyInput({ hint }: { hint?: string }) {
  const [value, setValue] = useState(getAdminKey)
  return (
    <label>
      {hint ?? 'Admin key (the ADMIN_API_KEY you set on the server)'}
      <input
        type="password"
        value={value}
        onChange={(e) => { setValue(e.target.value); setAdminKey(e.target.value) }}
        placeholder="Admin key"
        autoComplete="off"
      />
    </label>
  )
}
