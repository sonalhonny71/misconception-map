import { useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
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
import { ToastContainer, useToast } from './components/Toast'
import { api } from './api/client'

/**
 * Makes sure there is an anonymous learner (and token) before any page loads.
 * Pages call the API with that token, so it must exist first.
 */
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { learner, loading, setLearner } = useAuth()
  const { show } = useToast()
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (loading || learner) return
    let cancelled = false
    api
      .createLearner()
      .then((data) => {
        if (cancelled) return
        setLearner({ token: data.token, tokenHash: data.token_hash })
        show('Welcome! Your learning journey begins now.')
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [loading, learner, setLearner, show, attempt])

  if (failed && !learner) {
    return (
      <div className="shell">
        <div className="main">
          <main className="content">
            <div className="empty" role="alert">
              We couldn't reach the server. It may be waking up (this can take up to ~30 seconds on the free tier).
              <div className="mt-4">
                <button className="btn primary" onClick={() => { setFailed(false); setAttempt((n) => n + 1) }}>
                  Try again
                </button>
              </div>
            </div>
          </main>
        </div>
      </div>
    )
  }

  if (loading || !learner) {
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