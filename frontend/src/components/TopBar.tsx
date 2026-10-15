import { useLocation } from 'react-router-dom'
import { useAuthStore } from '../hooks/useAuth'

const routeLabels: Record<string, string> = {
  '/': 'Dashboard',
  '/map': 'Learning Map',
  '/practice': 'Practice & Quests',
  '/insights': 'Insights & Misconceptions',
  '/progress': 'Progress & Achievements',
  '/placement': 'Find My Level',
  '/journey': 'Learning Journey',
}

export function TopBar() {
  const location = useLocation()
  const { learner } = useAuthStore()

  const getLabel = (pathname: string) => {
    if (pathname.startsWith('/journey')) return 'Learning Journey'
    return routeLabels[pathname] || 'Learning'
  }

  return (
    <header className="topbar">
      <div className="crumb">
        Learning space <span aria-hidden="true"> / </span> <strong id="crumb-label">{getLabel(location.pathname)}</strong>
      </div>
      <div className="avatar" aria-label="Learner profile">
        {learner?.token ? learner.token.charAt(0).toUpperCase() : 'S'}
      </div>
    </header>
  )
}