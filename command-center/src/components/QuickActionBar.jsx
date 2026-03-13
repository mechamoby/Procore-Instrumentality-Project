import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const actions = [
  {
    id: 'search',
    label: 'Search Database',
    subtitle: 'Cross-project institutional memory',
    icon: '🔍',
  },
  {
    id: 'deep-dive',
    label: 'Request Deep Dive',
    subtitle: 'Detailed analysis on demand',
    icon: '📊',
  },
  {
    id: 'reports',
    label: 'View Reports',
    subtitle: 'Briefing history & archives',
    icon: '📋',
  },
  {
    id: 'radar',
    label: 'Add to Radar',
    subtitle: 'Track an item or pattern',
    icon: '📡',
  },
]

export default function QuickActionBar({ projectId = null, projectName = null }) {
  const navigate = useNavigate()
  const [toast, setToast] = useState(null)

  function handleClick(action) {
    if (action.id === 'radar') {
      navigate('/radar')
      return
    }
    const scope = projectName ? ` — ${projectName}` : ''
    setToast(`${action.label}${scope} (coming soon)`)
    setTimeout(() => setToast(null), 2000)
  }

  return (
    <div className="relative">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {actions.map((action) => (
          <button
            key={action.id}
            onClick={() => handleClick(action)}
            className="bg-surface border border-border rounded-lg px-4 py-3 text-left hover:bg-card transition-colors duration-200 cursor-pointer"
          >
            <div className="text-base mb-1">{action.icon}</div>
            <div className="text-xs font-medium text-text-primary">{action.label}</div>
            <div className="text-[11px] text-text-tertiary">{action.subtitle}</div>
          </button>
        ))}
      </div>
      {toast && (
        <div className="absolute -top-10 left-1/2 -translate-x-1/2 bg-card border border-border rounded px-4 py-2 text-xs text-text-secondary shadow-lg whitespace-nowrap">
          {toast}
        </div>
      )}
    </div>
  )
}
