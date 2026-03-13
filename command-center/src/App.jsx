import { Routes, Route, useParams, useLocation } from 'react-router-dom'
import TopNavBar from './components/TopNavBar'
import RadarSidebar from './components/RadarSidebar'
import DashboardOverview from './pages/DashboardOverview'
import ProjectDetail from './pages/ProjectDetail'
import RadarPage from './pages/RadarPage'
import { getProjectBySlug } from './data/mockData'

function SidebarWrapper() {
  const location = useLocation()
  const match = location.pathname.match(/\/project\/([^/]+)/)
  const slug = match ? match[1] : null
  const project = slug ? getProjectBySlug(slug) : null
  return <RadarSidebar projectId={project?.id || null} />
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-page-bg">
      <TopNavBar />
      <div className="flex flex-1 pt-14">
        <main className="flex-1 min-w-0 p-6">
          <Routes>
            <Route path="/" element={<DashboardOverview />} />
            <Route path="/project/:slug" element={<ProjectDetail />} />
            <Route path="/radar" element={<RadarPage />} />
          </Routes>
        </main>
        <aside className="w-[250px] shrink-0 border-l border-border p-4 overflow-y-auto h-[calc(100vh-3.5rem)] sticky top-14 hidden lg:block">
          <SidebarWrapper />
        </aside>
      </div>
    </div>
  )
}
