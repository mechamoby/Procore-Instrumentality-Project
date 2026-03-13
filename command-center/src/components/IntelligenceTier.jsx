import { useState } from 'react'

const tierStyles = {
  red: {
    bg: 'bg-status-red/[0.08]',
    border: 'border-l-[4px] border-l-status-red',
    text: 'text-status-red',
  },
  amber: {
    bg: 'bg-status-amber/[0.08]',
    border: 'border-l-[4px] border-l-status-amber',
    text: 'text-status-amber',
  },
  blue: {
    bg: 'bg-status-blue/[0.08]',
    border: 'border-l-[4px] border-l-status-blue',
    text: 'text-status-blue',
  },
}

export default function IntelligenceTier({ label, color, itemCount, defaultExpanded, children }) {
  const [expanded, setExpanded] = useState(defaultExpanded)
  const styles = tierStyles[color]

  return (
    <div className="rounded-lg overflow-hidden border border-border/50">
      <button
        onClick={() => setExpanded(!expanded)}
        className={`w-full ${styles.bg} ${styles.border} flex items-center justify-between px-4 py-3 cursor-pointer min-h-[44px]`}
      >
        <span className={`text-sm font-bold ${styles.text}`}>{label}</span>
        <div className="flex items-center gap-3">
          <span className={`text-[13px] font-bold ${styles.text}`}>
            {itemCount} {itemCount === 1 ? 'item' : 'items'}
          </span>
          <svg
            className={`w-4 h-4 ${styles.text} transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </div>
      </button>
      <div
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${expanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
      >
        <div className="overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  )
}
