import { Routes, Route, Navigate } from 'react-router-dom'
import { Sidebar } from './components/Sidebar'
import { TopBar } from './components/TopBar'
import { Dashboard } from './pages/Dashboard'
import { LearningMap } from './pages/LearningMap'
import { Practice } from './pages/Practice'
import { Insights } from './pages/Insights'
import { Progress } from './pages/Progress'
import { Placement } from './pages/Placement'
import { Journey } from './pages/Journey'
import { NotFound } from './pages/NotFound'
import { useAuth } from './hooks/useAuth'
import { ToastContainer } from './components/Toast'

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { learner, loading } = useAuth()
  if (loading) {
    return (
      <div className="shell">
        <Sidebar />
        <div className="main">
          <TopBar />
          <main className="content">
            <div className="skeleton h-8 w-48 mb-4" />
            <div className="skeleton h-6 w-96 mb-4" />
            <div className="skeleton h-6 w-72" />
          </main>
        </div>
      </div>
    )
  }
  return <>{children}</>
}

export default function App() {
  return (
    <PrivateRoute>
      <div className="shell">
        <Sidebar />
        <div className="main">
          <TopBar />
          <main className="content">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/map" element={<LearningMap />} />
              <Route path="/practice" element={<Practice />} />
              <Route path="/insights" element={<Insights />} />
              <Route path="/progress" element={<Progress />} />
              <Route path="/placement" element={<Placement />} />
              <Route path="/journey/:sessionId" element={<Journey />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </main>
          <footer className="footer">
            MisconceptionMap · Beyond right and wrong · Anonymous learning prototype. Your progress is saved under a random ID on our server so you can resume; no names or emails are collected. You can delete it any time.
          </footer>
        </div>
      </div>
      <ToastContainer />
    </PrivateRoute>
  )
}