import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import { DisplayMath } from '../components/MathDisplay'
import { AlertCircle, Info, CheckCircle, XCircle } from 'lucide-react'

const STATUS_ICONS: Record<string, React.ComponentType<any>> = {
  insufficient: Info,
  possible: AlertCircle,
  supported: CheckCircle,
}

const STATUS_COLORS: Record<string, string> = {
  insufficient: 'text-blue-600 bg-blue-50 border-blue-100',
  possible: 'text-amber-700 bg-amber-50 border-amber-100',
  supported: 'text-teal-700 bg-teal-50 border-teal-100',
}

export function Insights() {
  const { data: insights } = useQuery({
    queryKey: ['insights'],
    queryFn: api.getInsights,
  })

  if (!insights?.hypotheses?.length) {
    return (
      <section className="view active" id="insights">
        <div className="eyebrow">Evidence, not labels</div>
        <h1 className="h1">Insights & misconceptions</h1>
        <p className="lead">Possible explanations are based on your recorded responses and should be treated as hypotheses.</p>
        <div className="empty">No diagnostic evidence yet. Complete a diagnostic to see your learning clues.</div>
      </section>
    )
  }

  return (
    <section className="view active" id="insights">
      <div className="eyebrow">Evidence, not labels</div>
      <h1 className="h1">Insights & misconceptions</h1>
      <p className="lead">Possible explanations are based on your recorded responses and should be treated as hypotheses.</p>

      <div className="space-y-4">
        {insights.hypotheses.map((hyp: any, index: number) => {
          const StatusIcon = STATUS_ICONS[hyp.status] || Info
          const colorClass = STATUS_COLORS[hyp.status] || STATUS_COLORS.insufficient

          return (
            <div key={index} className="card">
              <div className="flex items-start gap-4">
                <div className={`p-3 rounded-xl border ${colorClass} flex-shrink-0`}>
                  <StatusIcon className="w-6 h-6" aria-hidden="true" />
                </div>
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3>{hyp.misconception_label}</h3>
                    <span className={`pill ${hyp.status === 'supported' ? 'done' : ''}`}>
                      {hyp.status === 'insufficient' ? 'Insufficient evidence' :
                       hyp.status === 'possible' ? 'Possible explanation' : 'Supported by evidence'}
                    </span>
                  </div>
                  <p className="text-muted mb-2">{hyp.wording || getStatusWording(hyp.status)}</p>
                  <DisplayMath children={hyp.step_explanation || ''} className="my-2" />
                  <p className="text-sm text-muted"><em>{hyp.why_it_matters}</em></p>

                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm text-indigo-600 hover:underline">View evidence trail</summary>
                    <div className="mt-3 space-y-2 text-sm">
                      {hyp.evidence_trail?.map((e: any, i: number) => (
                        <div key={i} className="p-3 bg-paper rounded-lg border border-line">
                          <div className="font-medium">{e.question}</div>
                          <div className="flex items-center gap-2 text-muted mt-1">
                            <span>Your answer:</span>
                            <span className="font-mono">{e.chosen_option}</span>
                            {e.misconception_suggested && (
                              <span className="text-amber-600">({getMisconceptionLabel(e.misconception_suggested)})</span>
                            )}
                          </div>
                          <div className="text-xs text-muted mt-1">Phase: {e.phase}</div>
                        </div>
                      ))}
                    </div>
                  </details>
                </div>
              </div>
            </div>
          )
        })}

        {/* Recent Evidence */}
        {insights.recent_evidence?.length > 0 && (
          <div className="card">
            <h3>Recent activity</h3>
            <div className="space-y-3 mt-4">
              {insights.recent_evidence.map((e: any, i: number) => (
                <div key={i} className="p-3 bg-paper rounded-lg border border-line">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className={e.is_correct ? 'text-teal-600' : 'text-red-600'}>
                        {e.is_correct ? <CheckCircle className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                      </span>
                      <div>
                        <div className="font-medium">{e.question}</div>
                        <div className="text-sm text-muted">{e.chosen_option}</div>
                      </div>
                    </div>
                    <span className="text-xs text-muted">{e.phase} · {new Date(e.date).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </section>
  )
}

function getStatusWording(status: string): string {
  return {
    insufficient: "We don't have enough evidence yet to say why.",
    possible: 'One possible explanation, still checking.',
    supported: 'The evidence supports this explanation.',
  }[status] || "We don't have enough evidence yet to say why."
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