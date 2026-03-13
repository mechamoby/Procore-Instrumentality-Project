import { getAllProjects, getCriticalItemCount } from '../data/mockData'
import ProjectHealthCard from '../components/ProjectHealthCard'
import ActivityFeed from '../components/ActivityFeed'
import QuickActionBar from '../components/QuickActionBar'

export default function DashboardOverview() {
  const projects = getAllProjects()
  const criticalCount = getCriticalItemCount()

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="max-w-[1400px]">
      <h1 className="text-xl font-medium text-text-primary mb-1">
        {greeting}, Moby.
      </h1>
      <p className="text-sm text-text-secondary mb-8">
        {criticalCount > 0
          ? `${criticalCount} critical items across your projects need attention today.`
          : 'No critical items across your projects today.'}
      </p>

      {projects.length === 0 ? (
        <div className="text-text-tertiary text-sm py-12 text-center">
          No active projects. Projects will appear here when data begins syncing.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4 mb-8">
          {projects.map((project) => (
            <ProjectHealthCard key={project.id} project={project} />
          ))}
        </div>
      )}

      <ActivityFeed />

      <div className="mt-8">
        <QuickActionBar />
      </div>
    </div>
  )
}
