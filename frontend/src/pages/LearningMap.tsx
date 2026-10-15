import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { CheckCircle, Clock, Lock, PlayCircle } from 'lucide-react'

const LEVEL_INFO = [
  { id: 1, name: 'Foundations', title: 'Arithmetic principles & integers', desc: 'Number lines, integer signs, and order of operations.' },
  { id: 2, name: 'Expressions', title: 'Expressions & like terms', desc: 'Substitution, grouping terms, and simplifying expressions.' },
  { id: 3, name: 'Algebra Essentials', title: 'Distributive property & inverses', desc: 'Expand brackets, handle negative multipliers, and use inverse operations.' },
  { id: 4, name: 'Equation Solver', title: 'Multi-step equations', desc: 'Solve equations with negative coefficients and variables on both sides.' },
  { id: 5, name: 'Challenge Lab', title: 'Real-world transfer & inequalities', desc: 'Apply algebra to rates, inequalities, and unfamiliar problems.' },
]

const STATUS_LABELS: Record<string, { label: string; color: string; icon: React.ComponentType<any> }> = {
  not_assessed: { label: 'Available to explore', color: 'text-muted', icon: Lock },
  evidence_of_difficulty: { label: 'Evidence of a difficulty', color: 'text-amber-600', icon: Clock },
  practicing: { label: 'Practicing', color: 'text-indigo-600', icon: PlayCircle },
  encouraging_evidence: { label: 'Encouraging evidence', color: 'text-teal-600', icon: CheckCircle },
  consistent_evidence: { label: 'Consistent evidence', color: 'text-teal-800', icon: CheckCircle },
  needs_more_practice: { label: 'Needs more practice', color: 'text-red-600', icon: Clock },
}

export function LearningMap() {
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all')

  const { data: levelsData } = useQuery({
    queryKey: ['levels'],
    queryFn: api.getLevels,
  })

  const levels = levelsData?.levels || LEVEL_INFO.map(l => ({ ...l, status: 'not_assessed', progress_percent: 0 }))

  const filteredLevels = levels.filter((level: any) => {
    if (filter === 'all') return true
    if (filter === 'completed') return level.status === 'consistent_evidence' || level.status === 'encouraging_evidence'
    if (filter === 'active') return level.status === 'practicing' || level.status === 'evidence_of_difficulty'
    return true
  })

  return (
    <section className="view active" id="learning-map">
      <div className="eyebrow">Curriculum navigator</div>
      <h1 className="h1">Your interactive learning pathway</h1>
      <p className="lead">Move through five levels at your pace. Select a level to start a short diagnostic.</p>

      <div className="filter-row">
        <button
          className={filter === 'all' ? 'active' : ''}
          onClick={() => setFilter('all')}
        >
          All levels
        </button>
        <button
          className={filter === 'active' ? 'active' : ''}
          onClick={() => setFilter('active')}
        >
          In progress
        </button>
        <button
          className={filter === 'completed' ? 'active' : ''}
          onClick={() => setFilter('completed')}
        >
          Completed
        </button>
      </div>

      <div className="level-grid" id="level-grid">
        {filteredLevels.map((level: any) => {
          const statusInfo = STATUS_LABELS[level.status] || STATUS_LABELS.not_assessed
          const StatusIcon = statusInfo.icon
          const isDone = level.status === 'consistent_evidence' || level.status === 'encouraging_evidence'
          const isActive = level.status === 'practicing' || level.status === 'evidence_of_difficulty'

          return (
            <article key={level.id} className="level-card">
              <div className="level-top">
                <span className={`pill ${isDone ? 'done' : ''}`}>
                  {isDone ? '✓ Completed' : isActive ? '● Current focus' : `LEVEL ${level.id}`}
                </span>
                <span className="muted">{level.id} / 5</span>
              </div>
              <h3>{level.name}: {level.title}</h3>
              <p>{level.description ?? level.desc}</p>
              <div className="progress-track">
                <div className="progress-fill" style={{ width: `${level.progress_percent}%` }} />
              </div>
              <p className={statusInfo.color}>
                <StatusIcon className="inline w-4 h-4 mr-1" aria-hidden="true" />
                {statusInfo.label}
              </p>
              <Link to={`/journey/new?level=${level.id}`} className={`btn ${isActive ? 'primary' : 'secondary'} mt-2`}>
                {isDone ? 'Practice again' : 'Start diagnostic'} →
              </Link>
            </article>
          )
        })}
        {filteredLevels.length === 0 && (
          <div className="empty">No levels match this filter yet.</div>
        )}
      </div>
    </section>
  )
}