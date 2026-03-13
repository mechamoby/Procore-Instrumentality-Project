import { useState, useEffect, useRef } from 'react'

const healthBorders = {
  red: 'border-l-status-red',
  amber: 'border-l-status-amber',
  green: 'border-l-status-green',
}

// Track which projects have already shown typewriter in this session
const shownTypewriter = new Set()

export default function SynthesisBanner({ project, itemCount }) {
  const text = project.cycle_summary
  const [displayText, setDisplayText] = useState('')
  const [done, setDone] = useState(false)
  const intervalRef = useRef(null)

  const alreadyShown = shownTypewriter.has(project.id)

  useEffect(() => {
    if (alreadyShown) {
      setDisplayText(text)
      setDone(true)
      return
    }

    let i = 0
    setDisplayText('')
    setDone(false)

    intervalRef.current = setInterval(() => {
      i++
      setDisplayText(text.slice(0, i))
      if (i >= text.length) {
        clearInterval(intervalRef.current)
        setDone(true)
        shownTypewriter.add(project.id)
      }
    }, 35)

    return () => clearInterval(intervalRef.current)
  }, [project.id, text, alreadyShown])

  const synthTime = new Date(project.last_synthesis_at).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })
  const nextTime = new Date(project.next_cycle_at).toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })

  return (
    <div
      className={`bg-surface border-l-[3px] ${healthBorders[project.overall_health]} rounded-r-lg p-5 mb-4`}
    >
      <div className="text-sm text-text-secondary mb-1">
        Welcome back, Moby.
      </div>
      <div className="text-xs text-text-tertiary mb-3">
        Last report issued at {synthTime}.{' '}
        {itemCount > 0
          ? `${itemCount} items require attention.`
          : 'No items require attention.'}
      </div>
      <p className="text-[15px] font-medium text-text-primary leading-relaxed min-h-[1.5em]">
        {displayText}
        {!done && <span className="animate-pulse">|</span>}
      </p>
      <div className="flex items-center gap-4 mt-3 text-[11px] text-text-tertiary">
        <span>Next cycle: {nextTime}</span>
        <span>·</span>
        <span className="capitalize">{project.confidence} confidence</span>
        <span>·</span>
        <span>{project.active_source_count} sources active</span>
      </div>
    </div>
  )
}
