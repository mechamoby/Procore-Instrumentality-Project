export default function StatsBar({ project, items }) {
  const criticalCount = items.filter((i) => i.severity === 'critical').length
  const highCount = items.filter((i) => i.severity === 'high').length

  const dailyLogDisplay =
    project.daily_log_status === 'current'
      ? { text: 'Current', color: 'text-status-green' }
      : { text: `Missing ${project.daily_log_status.replace('missing_', '')} days`, color: 'text-status-red' }

  const stats = [
    { label: 'Critical', value: criticalCount, color: criticalCount > 0 ? 'text-status-red' : 'text-text-primary' },
    { label: 'High', value: highCount, color: highCount > 0 ? 'text-status-amber' : 'text-text-primary' },
    { label: 'Open RFIs', value: project.open_rfi_count, color: 'text-text-primary' },
    { label: 'Overdue RFIs', value: project.overdue_rfi_count, color: project.overdue_rfi_count > 0 ? 'text-status-red' : 'text-text-primary' },
    { label: 'Open Submittals', value: project.open_submittal_count, color: 'text-text-primary' },
    { label: 'Daily Log', value: dailyLogDisplay.text, color: dailyLogDisplay.color, isText: true },
    { label: 'Complete', value: `${project.completion_pct}%`, color: 'text-text-primary', isText: true },
  ]

  return (
    <div className="grid grid-cols-7 gap-2 mb-4">
      {stats.map((stat) => (
        <div key={stat.label} className="bg-surface rounded-lg px-3 py-2.5 text-center">
          <div className={`text-base font-medium ${stat.color}`}>
            {stat.isText ? stat.value : stat.value}
          </div>
          <div className="text-[11px] text-text-tertiary mt-0.5">{stat.label}</div>
        </div>
      ))}
    </div>
  )
}
