import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DisplayMath } from '../components/MathDisplay'
import { Trophy, Star, Target, TrendingUp } from 'lucide-react'

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  not_assessed: { label: 'Not assessed', color: 'text-muted' },
  evidence_of_difficulty: { label: 'Evidence of a difficulty', color: 'text-amber-600' },
  practicing: { label: 'Practicing', color: 'text-indigo-600' },
  encouraging_evidence: { label: 'Encouraging evidence', color: 'text-teal-600' },
  consistent_evidence: { label: 'Consistent evidence', color: 'text-teal-800' },
  needs_more_practice: { label: 'Needs more practice', color: 'text-red-600' },
}

const ACHIEVEMENT_INFO: Record<string, { label: string; icon: React.ComponentType<any> }> = {
  'first-practice': { label: 'First practice completed', icon: Star },
  'first-retest': { label: 'First fresh retest completed', icon: Trophy },
}

export function Progress() {
  const { data: progress } = useQuery({
    queryKey: ['progress'],
    queryFn: api.getProgress,
  })

  if (!progress) {
    return (
      <section className="view active" id="progress">
        <div className="eyebrow">Your learning record</div>
        <h1 className="h1">Progress & achievements</h1>
        <p className="lead">A record of practice and retests completed.</p>
        <div className="empty">No activity yet. Start a diagnostic to create your first record.</div>
      </section>
    )
  }

  return (
    <section className="view active" id="progress">
      <div className="eyebrow">Your learning record</div>
      <h1 className="h1">Progress & achievements</h1>
      <p className="lead">A record of practice and retests completed.</p>

      <div className="stats">
        <div className="stat">
          <small>Total XP</small>
          <strong>{progress.total_xp || 0} XP</strong>
        </div>
        <div className="stat">
          <small>Levels with retest evidence</small>
          <strong>{progress.skills?.filter((s: any) => s.retest_count > 0).length || 0}/5</strong>
        </div>
        <div className="stat">
          <small>Recorded activities</small>
          <strong>{progress.history?.length || 0}</strong>
        </div>
      </div>

      {/* Skills Overview */}
      <div className="card">
        <h3>Skill progress</h3>
        <div className="space-y-4 mt-4">
          {progress.skills?.map((skill: any) => {
            const statusInfo = STATUS_LABELS[skill.status] || STATUS_LABELS.not_assessed
            return (
              <div key={skill.skill} className="p-4 bg-paper rounded-lg border border-line">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="font-medium">{LEVEL_NAMES[skill.level]}: {skill.skill.replace(/-/g, ' ')}</h4>
                    <span className={statusInfo.color}>{statusInfo.label}</span>
                  </div>
                  <div className="text-right">
                    {skill.last_retest_score !== null && (
                      <div className="text-sm">
                        Latest retest: <strong>{skill.last_retest_score}/{skill.last_retest_total}</strong>
                      </div>
                    )}
                    <div className="text-xs text-muted">{skill.retest_count} retest(s)</div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Achievements */}
      <div className="card mt-6">
        <h3>Achievements</h3>
        <div className="mt-4 flex flex-wrap gap-4">
          {Object.entries(ACHIEVEMENT_INFO).map(([id, info]) => {
            const earned = progress.achievements?.includes(info.label)
            const Icon = info.icon
            return (
              <div
                key={id}
                className={`flex items-center gap-3 p-4 rounded-xl border-2 ${earned ? 'border-teal-300 bg-teal-50' : 'border-line bg-paper opacity-50'}`}
              >
                <div className={`p-2 rounded-lg ${earned ? 'bg-teal-100 text-teal-700' : 'bg-line text-muted'}`}>
                  <Icon className="w-6 h-6" aria-hidden="true" />
                </div>
                <div>
                  <div className="font-medium">{info.label}</div>
                  <div className="text-sm text-muted">{earned ? 'Earned!' : 'Complete a practice set to unlock'}</div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* History */}
      <div className="card mt-6">
        <h3>Recent activity</h3>
        {progress.history?.length ? (
          <div className="mt-4 space-y-3">
            {progress.history.slice(0, 12).map((h: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-3 bg-paper rounded-lg border border-line">
                <div className="flex items-center gap-3">
                  <span className={`p-2 rounded-lg ${getPhaseColor(h.type)}`}>
                    {getPhaseIcon(h.type)}
                  </span>
                  <div>
                    <div className="font-medium">{h.type.charAt(0).toUpperCase() + h.type.slice(1)}</div>
                    <div className="text-sm text-muted">Level {h.level} · {new Date(h.date).toLocaleString()}</div>
                  </div>
                </div>
                <strong>{h.score}/{h.total}</strong>
              </div>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-muted">No activity yet. Start a diagnostic to create your first record.</p>
        )}
      </div>

      {/* Reset Button */}
      <div className="mt-6 text-center">
        <button
          onClick={handleReset}
          className="btn secondary text-red-600 border-red-300 hover:bg-red-50"
        >
          Reset my progress / delete my data
        </button>
      </div>
    </section>
  )
}

const LEVEL_NAMES: Record<number, string> = {
  1: 'Foundations',
  2: 'Expressions',
  3: 'Algebra Essentials',
  4: 'Equation Solver',
  5: 'Challenge Lab',
}

function getPhaseColor(type: string): string {
  const colors: Record<string, string> = {
    diagnostic: 'bg-blue-100 text-blue-700',
    followup: 'bg-purple-100 text-purple-700',
    check_understanding: 'bg-indigo-100 text-indigo-700',
    practice: 'bg-teal-100 text-teal-700',
    retest: 'bg-amber-100 text-amber-700',
  }
  return colors[type] || 'bg-line text-muted'
}

function getPhaseIcon(type: string) {
  // Simple text fallback
  return type.charAt(0).toUpperCase()
}

async function handleReset() {
  if (confirm('This will permanently delete all your progress. Are you sure?')) {
    try {
      await fetch('/api/learners/me', { method: 'DELETE', credentials: 'include' })
      localStorage.clear()
      window.location.reload()
    } catch (e) {
      alert('Failed to reset progress')
    }
  }
}