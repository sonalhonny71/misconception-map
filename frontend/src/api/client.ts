import { useAuthStore } from './hooks/useAuth'

const API_BASE = '/api'

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const { learner } = useAuthStore.getState()
  
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }
  
  if (learner?.token) {
    headers['Authorization'] = `Bearer ${learner.token}`
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ code: 'UNKNOWN', message: 'Request failed' }))
    throw new Error(error.message || `HTTP ${response.status}`)
  }

  if (response.status === 204) {
    return {} as T
  }

  return response.json()
}

export const api = {
  // Learners
  createLearner: () => request<{ token: string; token_hash: string }>('/learners', { method: 'POST' }),
  deleteLearner: () => request<void>('/learners/me', { method: 'DELETE' }),
  getSummary: () => request<{ total_xp: number; practice_sets_completed: number; latest_retest: any; active_level: number }>('/me/summary'),

  // Levels
  getLevels: () => request<{ levels: any[] }>('/levels'),

  // Sessions
  startSession: (level: number) => request<{ id: string; level: number; phase: string; step_index: number; status: string; started_at: string }>('/sessions', {
    method: 'POST',
    body: JSON.stringify({ level }),
  }),
  getQuestion: (sessionId: string) => request<any>(`/sessions/${sessionId}`),
  submitAnswer: (sessionId: string, servedItemId: string, optionId: string | null) => request<any>(`/sessions/${sessionId}/answer`, {
    method: 'POST',
    body: JSON.stringify({ served_item_id: servedItemId, option_id: optionId }),
  }),

  // Insights
  getInsights: () => request<any>('/insights'),

  // Progress
  getProgress: () => request<any>('/progress'),

  // Health
  health: () => request<{ status: string; database: string; timestamp: string }>('/health'),
}