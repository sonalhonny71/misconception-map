import { NavLink, useLocation } from 'react-router-dom'
import { LayoutDashboard, Map, BookOpen, BarChart2, TrendingUp, Target } from 'lucide-react'
import { useAuthStore } from '../hooks/useAuth'

const navItems = [
  { path: '/', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/map', label: 'Learning Map', icon: Map },
  { path: '/practice', label: 'Practice & Quests', icon: BookOpen },
  { path: '/insights', label: 'Insights', icon: BarChart2 },
  { path: '/progress', label: 'Progress', icon: TrendingUp },
  { path: '/placement', label: 'Find My Level', icon: Target },
]

export function Sidebar() {
  const location = useLocation()
  const { learner, clearLearner } = useAuthStore()

  return (
    <aside className="sidebar" aria-label="Main navigation">
      <div className="brand">
        <span className="brand-mark">M</span>
        MisconceptionMap
      </div>
      <div className="side-label">Your learning space</div>
      <nav className="nav" aria-label="Main navigation">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
            onClick={() => {}}
          >
            <span className="ico" aria-hidden="true">
              <item.icon size={22} strokeWidth={2} />
            </span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-note">
        <strong>Every answer is a clue.</strong>
        Misconceptions are hypotheses to investigate, not labels to attach to learners.
      </div>
    </aside>
  )
}