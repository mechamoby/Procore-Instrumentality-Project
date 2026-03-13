import { getAllRadarItems, getRadarItemsByProject } from '../data/mockData'

const priorityColors = {
  critical: 'border-l-status-red',
  high: 'border-l-status-amber',
  watch: 'border-l-status-blue',
}

const priorityLabels = {
  critical: 'Critical',
  high: 'High',
  watch: 'Watch',
}

const trendIndicators = {
  escalating: { icon: '↑', label: 'Escalating', color: 'text-status-red' },
  stable: { icon: '→', label: 'Stable', color: 'text-status-amber' },
  improving: { icon: '↓', label: 'Improving', color: 'text-status-green' },
  resolving: { icon: '↓', label: 'Resolving', color: 'text-status-green' },
}

export default function RadarSidebar({ projectId = null }) {
  const items = projectId
    ? getRadarItemsByProject(projectId)
    : getAllRadarItems()

  return (
    <div>
      <h2 className="text-sm font-medium text-text-primary mb-4">Radar</h2>
      {items.length === 0 ? (
        <p className="text-xs text-text-tertiary">No items being tracked.</p>
      ) : (
        <div className="flex flex-col gap-2">
          {items.map((item) => {
            const trend = trendIndicators[item.trend]
            return (
              <div
                key={item.id}
                className={`border-l-2 ${priorityColors[item.priority]} bg-card hover:bg-card-hover rounded-r px-3 py-2 cursor-pointer transition-colors duration-200`}
              >
                <div className="text-xs font-medium text-text-primary leading-tight mb-1">
                  {item.title}
                </div>
                {!projectId && (
                  <div className="text-[10px] text-text-tertiary mb-1">
                    {item.project_name}
                  </div>
                )}
                <div className="flex items-center gap-1.5 text-[10px]">
                  <span className="text-text-tertiary">
                    {priorityLabels[item.priority]}
                  </span>
                  <span className="text-text-tertiary">·</span>
                  <span className={trend.color}>
                    {trend.icon} {trend.label}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
