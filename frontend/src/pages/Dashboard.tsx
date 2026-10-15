import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useAuthStore } from '../hooks/useAuth'
import { useToast } from '../components/Toast'
import { ArrowRight, Target, MapPin } from 'lucide-react'
import { DisplayMath } from '../components/MathDisplay'

export function Dashboard() {
  const { learner, setLearner } = useAuthStore()
  const { show } = useToast()

  const { data: summary, isLoading } = useQuery({
    queryKey: ['summary'],
    queryFn: api.getSummary,
    enabled: !!learner,
  })

  const { data: levels } = useQuery({
    queryKey: ['levels'],
    queryFn: api.getLevels,
    enabled: !!learner,
  })

  // Initialize learner if not exists
  if (!learner && !isLoading) {
    api.createLearner().then((data) => {
      setLearner(data)
      show('Welcome! Your learning journey begins now.')
    }).catch(() => {
      show('Failed to start session. Please refresh.', 'error')
    })
    return <DashboardSkeleton />
  }

  if (!learner) return <DashboardSkeleton />

  const activeLevel = levels?.levels?.find((l: any) => l.id === summary?.active_level) || levels?.levels?.[2]
  const completedCount = levels?.levels?.filter((l: any) => l.status === 'consistent_evidence' || l.status === 'encouraging_evidence').length || 0

  return (
    <section className="view active" id="dashboard">
      <div className="hero">
        <div>
          <div className="eyebrow">Understand your thinking</div>
          <h1 className="h1">Learn from every answer.</h1>
          <p>MisconceptionMap looks beyond right and wrong. Find patterns in your answers, understand the reasoning behind them, and practice the next step that will help.</p>
          <div className="actions">
            <Link to="/map" className="btn primary">
              Start learning <ArrowRight className="ml-2 w-5 h-5" aria-hidden="true" />
            </Link>
            <Link to="/placement" className="btn secondary">
              <Target className="mr-2 w-5 h-5" aria-hidden="true" /> Find my level
            </Link>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit">
            <DisplayMath children="\\sum" />
          </div>
        </div>
      </div>

      <div className="stats">
        <div className="stat">
          <small>Total XP</small>
          <strong>{summary?.total_xp || 0} XP</strong>
        </div>
        <div className="stat">
          <small>Practice sets completed</small>
          <strong>{summary?.practice_sets_completed || 0}</strong>
        </div>
        <div className="stat">
          <small>Latest retest</small>
          <strong>{summary?.latest_retest ? `${summary.latest_retest.score}/${summary.latest_retest.total}` : '—'}</strong>
        </div>
      </div>

      <div className="section-head">
        <div>
          <h2>Pick up where you left off</h2>
          <p>Your progress is saved securely on our server.</p>
        </div>
        <Link to="/map" className="btn soft">Open learning map</Link>
      </div>

      <div className="two-col">
        <div className="card">
          <span className="pill">CURRENT FOCUS</span>
          <h3 style={{ marginTop: '12px' }}>{activeLevel?.name}: {activeLevel?.title}</h3>
          <p>{activeLevel?.description}</p>
          <Link to={`/journey/new?level=${activeLevel?.id}`} className="btn primary mt-4">
            Begin a diagnostic <ArrowRight className="ml-2 w-5 h-5" aria-hidden="true" />
          </Link>
        </div>
        <div className="card">
          <h3>How it works</h3>
          <p><strong>Answer → Diagnose → Understand → Practice → Retest</strong></p>
          <p>One answer is a clue, not a conclusion. The app gathers evidence before suggesting a possible explanation.</p>
          <div className="mt-4 p-4 bg-lavender rounded-xl">
            <p className="text-sm text-indigo-800">
              <strong>Honest feedback:</strong> We never say "you have this misconception." We say "your answer is consistent with..." and show the evidence.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

function DashboardSkeleton() {
  return (
    <section className="view active" id="dashboard">
      <div className="hero">
        <div>
          <div className="skeleton h-4 w-32 mb-4" />
          <div className="skeleton h-10 w-96 mb-4" />
          <div className="skeleton h-6 w-80 mb-6" />
          <div className="skeleton h-12 w-48" />
        </div>
        <div className="skeleton h-48 w-48 rounded-full" />
      </div>
      <div className="stats">
        <div className="stat skeleton h-24" />
        <div className="stat skeleton h-24" />
        <div className="stat skeleton h-24" />
      </div>
      <div className="skeleton h-8 w-48 mb-4" />
      <div className="two-col">
        <div className="card skeleton h-64" />
        <div className="card skeleton h-64" />
      </div>
    </section>
  )
}