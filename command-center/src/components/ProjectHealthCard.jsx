import { useNavigate } from 'react-router-dom'
import { getIntelligenceItemsByProject } from '../data/mockData'

const healthColors = {
  red: { border: 'border-t-status-red', badge: 'bg-status-red/15 text-status-red', dot: 'bg-status-red' },
  amber: { border: 'border-t-status-amber', badge: 'bg-status-amber/15 text-status-amber', dot: 'bg-status-amber' },
  green: { border: 'border-t-status-green', badge: 'bg-status-green/15 text-status-green', dot: 'bg-status-green' },
}

const healthLabels = {
  red: 'Action Required',
  amber: 'Needs Attention',
  green: 'On Track',
}

function formatTimestamp(iso) {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now - d
  const diffH = Math.floor(diffMs / 3_600_000)
  if (diffH < 1) return 'Just now'
  if (diffH < 24) return `${diffH}h ago`
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export default function ProjectHealthCard({ project }) {
  const navigate = useNavigate()
  const colors = healthColors[project.overall_health]
  const items = getIntelligenceItemsByProject(project.id)
  const criticalCount = items.filter((i) => i.severity === 'critical').length
  const highCount = items.filter((i) => i.severity === 'high').length
  const watchCount = items.filter((i) => i.severity === 'watch').length

  const confidenceLabel =
    project.confidence === 'high'
      ? `High confidence — ${project.active_source_count} sources active`
      : `Limited data — ${project.active_source_count} sources active`

  return (
    <div
      onClick={() => navigate(`/project/${project.slug}`)}
      className={`bg-card hover:bg-card-hover border-t-[3px] ${colors.border} border border-border rounded-lg p-5 cursor-pointer transition-colors duration-200`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <h3 className="text-[15px] font-medium text-text-primary leading-tight">
            {project.name}
          </h3>
          <span className="text-xs text-text-tertiary">{project.number}</span>
        </div>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${colors.badge}`}>
          {healthLabels[project.overall_health]}
        </span>
      </div>

      <p className="text-xs text-text-secondary leading-relaxed mb-4">
        {project.cycle_summary}
      </p>

      <div className="flex items-center gap-3 text-xs mb-3">
        {criticalCount > 0 && (
          <span className="text-status-red font-medium">{criticalCount} critical</span>
        )}
        {highCount > 0 && (
          <span className="text-status-amber font-medium">{highCount} high</span>
        )}
        {watchCount > 0 && (
          <span className="text-text-tertiary">{watchCount} watch</span>
        )}
        {criticalCount === 0 && highCount === 0 && watchCount === 0 && (
          <span className="text-text-tertiary">No open items</span>
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] text-text-tertiary">
        <span>{confidenceLabel}</span>
        <span>Updated {formatTimestamp(project.last_synthesis_at)}</span>
      </div>
    </div>
  )
}
