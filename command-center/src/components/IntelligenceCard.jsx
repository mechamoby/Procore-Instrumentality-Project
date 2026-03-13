import { useState } from 'react'

const severityStyles = {
  critical: { border: 'border-l-status-red', badge: 'bg-status-red/15 text-status-red', badgeText: 'Action required' },
  high: { border: 'border-l-status-amber', badge: 'bg-status-amber/15 text-status-amber', badgeText: 'Attention' },
  watch: { border: 'border-l-status-blue', badge: 'bg-status-blue/15 text-status-blue', badgeText: 'Watch' },
}

const trendDisplay = {
  escalating: { icon: '↑', label: 'Escalating', color: 'text-status-red' },
  stable: { icon: '→', label: 'Stable', color: 'text-status-amber' },
  improving: { icon: '↓', label: 'Improving', color: 'text-status-green' },
  resolving: { icon: '↓', label: 'Resolving', color: 'text-status-green' },
}

const docIcons = {
  daily_log: '📋', rfi: '📝', submittal: '📦', drawing: '📐', email: '✉️',
  inspection: '🔍', schedule: '📅', correspondence: '💬', spec: '📄', survey: '📏',
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const hours = Math.floor(diffMs / 3_600_000)
  if (hours < 1) return 'Just now'
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function IntelligenceCard({ item, isExpanded, onToggle }) {
  const [feedback, setFeedback] = useState(null)
  const styles = severityStyles[item.severity]
  const trend = trendDisplay[item.trend]

  function handleFeedback(type) {
    setFeedback(type)
    console.log({ item_id: item.id, feedback: type })
  }

  return (
    <div
      className={`bg-card hover:bg-card-hover border border-border rounded-lg border-l-[3px] ${styles.border} cursor-pointer transition-colors duration-200`}
      onClick={onToggle}
    >
      {/* Surface layer */}
      <div className="p-3.5">
        <div className="flex items-center gap-2 mb-2">
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${styles.badge}`}>
            {styles.badgeText}
          </span>
          <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-border/50 text-text-secondary">
            {item.category}
          </span>
        </div>
        <h4 className="text-[13px] font-bold text-text-primary leading-tight mb-1.5 line-clamp-2">
          {item.title}
        </h4>
        <p className="text-xs text-text-secondary leading-relaxed mb-2.5 line-clamp-3">
          {item.summary}
        </p>
        <div className="flex items-center gap-2 text-[11px] text-text-tertiary">
          <span>{item.source_count} sources</span>
          <span>·</span>
          <span>{timeAgo(item.timestamp)}</span>
          <span>·</span>
          <span className={trend.color}>
            {trend.icon} {trend.label}
          </span>
        </div>
      </div>

      {/* Detail layer */}
      <div
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${isExpanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="overflow-hidden">
          <div className="border-t border-border px-3.5 py-3.5">
            {/* Full summary */}
            <p className="text-xs text-text-secondary leading-relaxed mb-4">
              {item.full_summary}
            </p>

            {/* Evidence chain */}
            {item.evidence_chain && item.evidence_chain.length > 0 && (
              <div className="mb-4">
                <h5 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">
                  Evidence
                </h5>
                <div className="flex flex-col gap-1.5">
                  {item.evidence_chain.map((ev, i) => (
                    <a
                      key={i}
                      href={ev.procore_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-2 text-xs text-text-secondary hover:text-status-blue transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <span className="text-sm">{docIcons[ev.type] || '📄'}</span>
                      <span className="flex-1 truncate">{ev.title}</span>
                      <span className="text-[10px] text-text-tertiary shrink-0">
                        {new Date(ev.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                      </span>
                    </a>
                  ))}
                </div>
              </div>
            )}

            {/* Recommended actions */}
            {item.recommended_actions && item.recommended_actions.length > 0 && (
              <div className="mb-4">
                <h5 className="text-[11px] font-medium text-text-tertiary uppercase tracking-wider mb-2">
                  Recommended Actions
                </h5>
                <ul className="flex flex-col gap-1">
                  {item.recommended_actions.map((action, i) => (
                    <li key={i} className="text-xs text-text-secondary leading-relaxed pl-3 relative before:content-['•'] before:absolute before:left-0 before:text-text-tertiary">
                      {action}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Technical metadata */}
            <div className="flex items-center flex-wrap gap-x-3 gap-y-1 text-[10px] text-text-tertiary mb-3">
              <span>{item.intelligence_type}</span>
              <span>·</span>
              <span>{item.confidence_pct}% confidence</span>
              <span>·</span>
              <span className={trend.color}>{trend.icon} {trend.label}</span>
              <span>·</span>
              <span>Updated {timeAgo(item.timestamp)}</span>
            </div>

            {/* Feedback buttons */}
            <div className="flex items-center gap-2">
              {['useful', 'not_useful', 'already_known'].map((type) => {
                const labels = { useful: 'Useful', not_useful: 'Not Useful', already_known: 'Already Known' }
                const isActive = feedback === type
                return (
                  <button
                    key={type}
                    onClick={(e) => { e.stopPropagation(); handleFeedback(type) }}
                    className={`text-[11px] px-2.5 py-1 rounded border transition-colors cursor-pointer ${
                      isActive
                        ? 'border-status-blue bg-status-blue/10 text-status-blue'
                        : 'border-border text-text-tertiary hover:text-text-secondary hover:border-text-tertiary'
                    }`}
                  >
                    {labels[type]}
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
