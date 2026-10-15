import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlayCircle, BookOpen, Calculator, FunctionSquare, Zap } from 'lucide-react'

const LEVELS = [
  { id: 1, name: 'Foundations', title: 'Arithmetic principles & integers', desc: 'Number lines, integer signs, and order of operations.', icon: Calculator },
  { id: 2, name: 'Expressions', title: 'Expressions & like terms', desc: 'Substitution, grouping terms, and simplifying expressions.', icon: FunctionSquare },
  { id: 3, name: 'Algebra Essentials', title: 'Distributive property & inverses', desc: 'Expand brackets, handle negative multipliers, and use inverse operations.', icon: BookOpen },
  { id: 4, name: 'Equation Solver', title: 'Multi-step equations', desc: 'Solve equations with negative coefficients and variables on both sides.', icon: PlayCircle },
  { id: 5, name: 'Challenge Lab', title: 'Real-world transfer & inequalities', desc: 'Apply algebra to rates, inequalities, and unfamiliar problems.', icon: Zap },
]

export function Placement() {
  const navigate = useNavigate()
  const [selectedLevel, setSelectedLevel] = useState(3)

  const handleStart = () => {
    navigate(`/journey/new?level=${selectedLevel}`)
  }

  return (
    <section className="view active" id="placement">
      <div className="eyebrow">Starting point</div>
      <h1 className="h1">Find your level</h1>
      <p className="lead">Choose a starting level. This is a starting point, not a permanent label; you can change it any time.</p>

      <div className="card">
        <h3>Which topic would you like to start with?</h3>
        <div className="options mt-6" id="placement-options">
          {LEVELS.map((level) => (
            <label
              key={level.id}
              className={`option ${selectedLevel === level.id ? 'selected' : ''}`}
              onClick={() => setSelectedLevel(level.id)}
            >
              <input
                type="radio"
                name="placement"
                value={level.id}
                checked={selectedLevel === level.id}
                onChange={() => setSelectedLevel(level.id)}
              />
              <span>
                <level.icon className="w-5 h-5 mr-3 text-indigo-600" aria-hidden="true" />
                <div>
                  <strong>{level.id}. {level.name}</strong>
                  <br />
                  <small className="muted">{level.desc}</small>
                </div>
              </span>
            </label>
          ))}
        </div>
        <div className="actions mt-6">
          <button className="btn primary" onClick={handleStart}>
            <PlayCircle className="mr-2 w-5 h-5" aria-hidden="true" />
            Start diagnostic
          </button>
        </div>
      </div>
    </section>
  )
}