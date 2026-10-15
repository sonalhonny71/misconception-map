import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DisplayMath } from '../components/MathDisplay'

export function Practice() {
  const { data: insights } = useQuery({
    queryKey: ['insights'],
    queryFn: api.getInsights,
  })

  const topHypothesis = insights?.hypotheses?.[0]

  if (!topHypothesis) {
    return (
      <section className="view active" id="practice">
        <div className="eyebrow">Targeted learning</div>
        <h1 className="h1">Practice & quests</h1>
        <p className="lead">Practice questions are selected for the skill you are working on.</p>
        <div className="empty">Complete a diagnostic first, or choose a level from the Learning Map.</div>
      </section>
    )
  }

  return (
    <section className="view active" id="practice">
      <div className="eyebrow">Targeted learning</div>
      <h1 className="h1">Practice & quests</h1>
      <p className="lead">Practice questions are selected for the skill you are working on.</p>

      <div className="card">
        <span className="pill">RECOMMENDED FOCUS</span>
        <h3 style={{ marginTop: '12px' }}>{topHypothesis.misconception_label}</h3>
        <p className="mt-2">{getMisconceptionDescription(topHypothesis.misconception_id)}</p>
        <DisplayMath children={topHypothesis.step_explanation || ''} className="mt-2" />
        <p className="mt-2 text-sm text-muted"><em>{topHypothesis.why_it_matters}</em></p>

        <div className="mt-4">
          <strong>Evidence trail:</strong>
          <ul className="mt-2 space-y-1 text-sm">
            {topHypothesis.evidence_trail?.slice(0, 3).map((e: any, i: number) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-muted">•</span>
                <span>{e.question}</span>
                <span className="text-muted">→</span>
                <span className="font-mono">{e.chosen_option}</span>
                {e.misconception_suggested && (
                  <span className="text-amber-600">({getMisconceptionLabel(e.misconception_suggested)})</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-6">
        <p className="text-sm text-muted">Practice questions for this skill will appear here after starting a diagnostic session.</p>
      </div>
    </section>
  )
}

function getMisconceptionLabel(id: string): string {
  const labels: Record<string, string> = {
    DIST_PARTIAL: 'Partial Distribution',
    DIST_NEG_SIGN: 'Negative Sign Distribution',
    LIKE_UNLIKE: 'Combining Unlike Terms',
    LIKE_NEG_COEFF: 'Negative Coefficient Sign Errors',
    SUBST_ORDER: 'Substitution Without Multiplication',
    INV_WRONG_OP: 'Wrong Inverse Operation',
    INV_ORDER: 'Inverse Operations in Wrong Order',
    INV_ONE_SIDE: 'Operation Applied to One Side Only',
    INV_NEG_DIV: 'Sign Lost Dividing by Negative',
    INT_COMPARE_ABS: 'Comparing Absolute Values',
    ORDER_OPS: 'Order of Operations',
    INEQ_FLIP: 'Inequality Sign Flip',
    ARITHMETIC_SLIP: 'Arithmetic Slip',
    UNCLEAR: 'Unclear Pattern',
  }
  return labels[id] || id
}

function getMisconceptionDescription(id: string): string {
  const descs: Record<string, string> = {
    DIST_PARTIAL: 'The multiplier was applied to only the first term inside the brackets.',
    DIST_NEG_SIGN: 'A negative multiplier was not correctly applied to both terms, especially negative × negative.',
    LIKE_UNLIKE: 'Terms with different variables or a variable and a constant were combined.',
    LIKE_NEG_COEFF: 'Sign errors when combining negative coefficients.',
    SUBST_ORDER: 'A value was substituted for a variable but the coefficient was not multiplied.',
    INV_WRONG_OP: 'The inverse operation was not correctly chosen (e.g., adding instead of subtracting to undo addition).',
    INV_ORDER: 'Inverse operations were applied in the wrong sequence or stopped before the variable was isolated.',
    INV_ONE_SIDE: 'An operation was applied to only one side of the equation.',
    INV_NEG_DIV: 'The negative sign was lost when dividing both sides by a negative coefficient.',
    INT_COMPARE_ABS: 'Numbers were compared by absolute size rather than position on the number line.',
    ORDER_OPS: 'Operations were performed left-to-right instead of following precedence rules.',
    INEQ_FLIP: 'The inequality direction was not reversed when multiplying or dividing by a negative number.',
    ARITHMETIC_SLIP: 'A calculation error unrelated to the algebraic concept.',
    UNCLEAR: 'The answer does not match a known misconception pattern; more evidence is needed.',
  }
  return descs[id] || ''
}