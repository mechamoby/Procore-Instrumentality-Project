import { useParams, useNavigate } from 'react-router-dom'
import { getProjectBySlug, getIntelligenceItemsByProject } from '../data/mockData'
import SynthesisBanner from '../components/SynthesisBanner'
import StatsBar from '../components/StatsBar'
import IntelligenceTier from '../components/IntelligenceTier'
import IntelligenceCard from '../components/IntelligenceCard'
import QuickActionBar from '../components/QuickActionBar'
import { useState } from 'react'

export default function ProjectDetail() {
  const { slug } = useParams()
  const navigate = useNavigate()
  const project = getProjectBySlug(slug)

  if (!project) {
    return (
      <div className="text-text-tertiary text-sm py-12 text-center">
        Project not found.
      </div>
    )
  }

  const items = getIntelligenceItemsByProject(project.id)
  const criticalItems = items.filter((i) => i.severity === 'critical')
  const highItems = items.filter((i) => i.severity === 'high')
  const watchItems = items.filter((i) => i.severity === 'watch')

  return (
    <div className="max-w-[1400px]">
      {/* Breadcrumb + Header */}
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={() => navigate('/')}
          className="text-xs text-status-blue hover:text-status-blue/80 transition-colors cursor-pointer"
        >
          ← All projects
        </button>
      </div>
      <ProjectHeader project={project} />

      <SynthesisBanner project={project} itemCount={criticalItems.length + highItems.length} />

      <StatsBar project={project} items={items} />

      {/* Intelligence Tiers */}
      <div className="flex flex-col gap-3 mt-6">
        <TierWithCards
          label="Action required"
          color="red"
          items={criticalItems}
          defaultExpanded
        />
        <TierWithCards
          label="Attention"
          color="amber"
          items={highItems}
          defaultExpanded
        />
        <TierWithCards
          label="Tracking"
          color="blue"
          items={watchItems}
          defaultExpanded={false}
        />
      </div>

      <div className="mt-8">
        <QuickActionBar projectId={project.id} projectName={project.name} />
      </div>
    </div>
  )
}

function ProjectHeader({ project }) {
  const healthColors = {
    red: 'bg-status-red',
    amber: 'bg-status-amber',
    green: 'bg-status-green',
  }
  const healthLabels = {
    red: 'Action Required',
    amber: 'Needs Attention',
    green: 'On Track',
  }
  const badgeColors = {
    red: 'bg-status-red/15 text-status-red',
    amber: 'bg-status-amber/15 text-status-amber',
    green: 'bg-status-green/15 text-status-green',
  }

  return (
    <div className="flex items-center gap-3 mb-4">
      <span className={`w-2.5 h-2.5 rounded-full ${healthColors[project.overall_health]}`} />
      <h1 className="text-lg font-medium text-text-primary">{project.name}</h1>
      <span className="text-xs text-text-tertiary">{project.number}</span>
      <span className={`text-xs font-medium px-2 py-0.5 rounded ${badgeColors[project.overall_health]}`}>
        {healthLabels[project.overall_health]}
      </span>
    </div>
  )
}

function TierWithCards({ label, color, items, defaultExpanded }) {
  const [expandedCardId, setExpandedCardId] = useState(null)

  function handleCardClick(id) {
    setExpandedCardId((prev) => (prev === id ? null : id))
  }

  return (
    <IntelligenceTier
      label={label}
      color={color}
      itemCount={items.length}
      defaultExpanded={defaultExpanded}
    >
      {items.length > 0 ? (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-2.5 p-3">
          {items.map((item) => (
            <IntelligenceCard
              key={item.id}
              item={item}
              isExpanded={expandedCardId === item.id}
              onToggle={() => handleCardClick(item.id)}
            />
          ))}
        </div>
      ) : (
        <div className="p-4 text-xs text-text-tertiary">
          No {label.toLowerCase()} items for this project.
        </div>
      )}
    </IntelligenceTier>
  )
}
