const API_BASE = '/api'

async function fetchJSON(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json()
}

// Live API calls — fall back to mock data if unavailable
export async function getDashboardOverview() {
  return fetchJSON('/dashboard/overview')
}

export async function getProjectSynthesis(projectId) {
  return fetchJSON(`/projects/${projectId}/synthesis/latest`)
}

export async function getProjectStats(projectId) {
  return fetchJSON(`/projects/${projectId}/stats`)
}

export async function getIntelligenceItems(projectId) {
  return fetchJSON(`/projects/${projectId}/intelligence-items?include=evidence`)
}

export async function getRadarItems(projectId) {
  return fetchJSON(`/projects/${projectId}/radar-items`)
}

export async function getRecentSignals() {
  return fetchJSON('/signals/recent')
}

export async function submitFeedback(itemId, feedback) {
  return fetch(`${API_BASE}/intelligence-items/${itemId}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ feedback }),
  })
}
