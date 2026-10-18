import { useParams } from 'react-router-dom'

export default function ComingSoon() {
  const { slug } = useParams()
  const name = (slug ?? 'this page').replace(/-/g, ' ')
  return (
    <div className="empty-card">
      <h2 style={{ textTransform: 'capitalize' }}>{name}</h2>
      <p>Not implemented yet. This section is planned for a later milestone; Milestone 1 covers the Dashboard only.</p>
    </div>
  )
}
