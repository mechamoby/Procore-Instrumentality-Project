import { useState } from 'react'
import { getRecentActivity } from '../data/mockData'

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export default function ActivityFeed() {
  const allEntries = getRecentActivity()
  const [expanded, setExpanded] = useState(false)
  const entries = expanded ? allEntries : allEntries.slice(0, 10)

  if (allEntries.length === 0) {
    return (
      <div className="text-xs text-text-tertiary py-4">No recent activity.</div>
    )
  }

  return (
    <div className="mt-8">
      <h2 className="text-sm font-medium text-text-primary mb-3 pb-2 border-b border-border">
        Live activity
      </h2>
      <div className="flex flex-col">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className="flex items-start gap-3 py-2.5 border-b border-border/50 last:border-0"
          >
            <div className="flex items-center gap-2 shrink-0 w-12">
              {entry.is_critical && (
                <span className="w-2 h-2 rounded-full bg-status-red shrink-0" />
              )}
              <span className="text-[11px] text-text-tertiary tabular-nums">
                {formatTime(entry.timestamp)}
              </span>
            </div>
            <p className="text-xs text-text-secondary leading-relaxed flex-1">
              {entry.description}
            </p>
            <span className="text-[10px] text-text-tertiary bg-surface px-2 py-0.5 rounded shrink-0">
              {entry.project_name}
            </span>
          </div>
        ))}
      </div>
      {allEntries.length > 10 && !expanded && (
        <button
          onClick={() => setExpanded(true)}
          className="text-xs text-status-blue hover:text-status-blue/80 mt-2 transition-colors"
        >
          Show more ({allEntries.length - 10} more)
        </button>
      )}
    </div>
  )
}
