import { NavLink } from 'react-router-dom'
import { useState, useEffect } from 'react'

export default function TopNavBar() {
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 60_000)
    return () => clearInterval(timer)
  }, [])

  const dateStr = now.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
  const timeStr = now.toLocaleTimeString('en-US', {
    hour: 'numeric',
    minute: '2-digit',
  })

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 h-14 bg-surface border-b border-border flex items-center px-6">
      {/* Logo / Wordmark */}
      <div className="flex items-center gap-2 mr-8">
        <div className="w-7 h-7 rounded bg-status-blue flex items-center justify-center text-white font-bold text-sm">
          S
        </div>
        <span className="text-text-primary font-semibold text-base tracking-tight">
          SteelSync
        </span>
      </div>

      {/* View Tabs */}
      <div className="flex items-center gap-1">
        <NavLink
          to="/"
          end
          className={({ isActive }) =>
            `px-3 py-1.5 rounded text-sm font-medium transition-colors duration-200 ${
              isActive
                ? 'bg-card text-text-primary'
                : 'text-text-secondary hover:text-text-primary hover:bg-card/50'
            }`
          }
        >
          Overview
        </NavLink>
        <NavLink
          to="/radar"
          className={({ isActive }) =>
            `px-3 py-1.5 rounded text-sm font-medium transition-colors duration-200 ${
              isActive
                ? 'bg-card text-text-primary'
                : 'text-text-secondary hover:text-text-primary hover:bg-card/50'
            }`
          }
        >
          Radar
        </NavLink>
      </div>

      {/* Right side: date/time + avatar */}
      <div className="ml-auto flex items-center gap-4">
        <div className="text-right">
          <div className="text-xs text-text-secondary leading-tight">{dateStr}</div>
          <div className="text-xs text-text-tertiary leading-tight">{timeStr}</div>
        </div>
        <div className="w-8 h-8 rounded-full bg-card border border-border flex items-center justify-center text-text-secondary text-xs font-medium">
          M
        </div>
      </div>
    </nav>
  )
}
