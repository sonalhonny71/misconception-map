import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import { useToast } from '../components/Toast'
import { DisplayMath, InlineMath } from '../components/MathDisplay'
import { Loader2, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react'

interface QuestionOption {
  id: string
  text: string
}

interface QuestionData {
  served_item_id: string
  item_id: string
  prompt: string
  options: QuestionOption[]
  step_label: string
  phase: string
  step_index: number
  total_steps: number
}

interface FeedbackData {
  is_correct: boolean
  explanation: string
  step_note: string | null
  misconception_id: string | null
  next_phase: string
  next_step_label: string
  xp_awarded: number
}

interface AnswerResponse {
  feedback: FeedbackData
  next_question: QuestionData | null
  session: any
}

export function Journey() {
  const { sessionId } = useParams()
  const [searchParams] = useSearchParams()
  const levelParam = searchParams.get('level')
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { show } = useToast()

  const [session, setSession] = useState<any>(null)
  const [question, setQuestion] = useState<QuestionData | null>(null)
  const [feedback, setFeedback] = useState<FeedbackData | null>(null)
  const [selectedOption, setSelectedOption] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [showNext, setShowNext] = useState(false)

  // Start or resume session
  const startMutation = useMutation({
    mutationFn: (level: number) => api.startSession(level),
    onSuccess: (data) => {
      setSession(data)
      fetchQuestion(data.id)
    },
    onError: () => show('Failed to start session', 'error'),
  })

  // Fetch current question
  const fetchQuestion = async (sessionId: string) => {
    try {
      const data = await api.getQuestion(sessionId)
      setQuestion(data)
      setSelectedOption(null)
      setSubmitted(false)
      setShowNext(false)
      setFeedback(null)
    } catch (e: any) {
      if (e.message.includes('complete') || e.message.includes('409')) {
        navigate('/progress')
      } else {
        show('Failed to load question', 'error')
      }
    }
  }

  // Submit answer
  const answerMutation = useMutation({
    mutationFn: ({ sessionId, servedItemId, optionId }: { sessionId: string; servedItemId: string; optionId: string | null }) =>
      api.submitAnswer(sessionId, servedItemId, optionId),
    onSuccess: (data) => {
      setFeedback(data.feedback)
      setSubmitted(true)
      setShowNext(true)

      if (data.feedback.xp_awarded > 0) {
        show(`+${data.feedback.xp_awarded} XP!`, 'success')
      }

      if (data.next_question) {
        setQuestion(data.next_question)
      } else if (data.session?.status === 'completed') {
        navigate('/progress')
      }
    },
    onError: () => show('Failed to submit answer', 'error'),
  })

  // Initialize
  useEffect(() => {
    if (sessionId === 'new' && levelParam) {
      startMutation.mutate(parseInt(levelParam))
    } else if (sessionId !== 'new') {
      fetchQuestion(sessionId)
    }
  }, [sessionId, levelParam])

  const handleSubmit = () => {
    if (!selectedOption && selectedOption !== '') return
    if (!session || !question) return

    answerMutation.mutate({
      sessionId: session.id,
      servedItemId: question.served_item_id,
      optionId: selectedOption,
    })
  }

  const handleNext = () => {
    setSelectedOption(null)
    setSubmitted(false)
    setShowNext(false)
    setFeedback(null)
  }

  if (!question && !startMutation.isPending) {
    return (
      <div className="skeleton h-8 w-48 mb-4" />
    )
  }

  if (!question) return null

  const phaseLabels: Record<string, string> = {
    diagnostic: `Diagnostic · Question ${question.step_index + 1} of ${question.total_steps}`,
    followup: 'Follow-up · Gathering evidence',
    check_understanding: `Check Understanding · Question ${question.step_index + 1} of ${question.total_steps}`,
    practice: `Targeted practice · Question ${question.step_index + 1} of 3`,
    retest: `Fresh retest · Question ${question.step_index + 1} of 3`,
  }

  const phaseIntros: Record<string, string> = {
    diagnostic: 'Choose the answer that best matches your thinking.',
    followup: 'One answer isn\'t enough to identify a misconception. This follow-up helps us distinguish possible explanations.',
    check_understanding: 'Let\'s check your understanding with a different type of question.',
    practice: 'Work through these three targeted questions. Read the explanation after each answer.',
    retest: 'These are fresh questions to check for evidence of improvement.',
  }

  return (
    <section className="view active" id="journey">
      <div className="eyebrow" id="journey-step">{phaseLabels[question.phase] || 'Question'}</div>
      <h1 className="h1" id="journey-title">
        {question.phase === 'followup' ? 'Let\'s check one more idea.' :
         question.phase === 'practice' ? 'Practice the next step.' :
         question.phase === 'retest' ? 'Let\'s see what changed.' :
         'Let\'s investigate your thinking.'}
      </h1>
      <p className="lead" id="journey-intro">{phaseIntros[question.phase] || 'Choose the answer that best matches your thinking.'}</p>

      <div id="journey-area">
        <div className="question-card">
          <span className="pill">LEVEL {session?.level || levelParam} · {LEVEL_INFO[session?.level - 1]?.name?.toUpperCase() || 'ALGEBRA ESSENTIALS'}</span>
          <h2 style={{ marginTop: '16px' }}>
            <DisplayMath children={question.prompt} />
          </h2>

          <form onSubmit={(e) => { e.preventDefault(); handleSubmit() }}>
            <div className="options" role="radiogroup" aria-label="Answer options">
              {question.options.map((option) => (
                <label
                  key={option.id}
                  className={`option ${selectedOption === option.id ? 'selected' : ''} ${submitted && option.id === question.correct_option_id ? 'correct' : ''} ${submitted && selectedOption === option.id && !feedback?.is_correct ? 'incorrect' : ''}`}
                >
                  <input
                    type="radio"
                    name="answer"
                    value={option.id}
                    checked={selectedOption === option.id}
                    onChange={() => !submitted && setSelectedOption(option.id)}
                    disabled={submitted}
                    required
                    aria-label={option.text}
                  />
                  <span>
                    <InlineMath children={option.text} />
                  </span>
                </label>
              ))}
            </div>

            {feedback && (
              <div id="answer-feedback" className={`notice ${feedback.is_correct ? 'good' : 'warn'} mt-4`} role="alert">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {feedback.is_correct ? (
                      <CheckCircle className="w-5 h-5 text-teal-600" aria-hidden="true" />
                    ) : (
                      <XCircle className="w-5 h-5 text-red-600" aria-hidden="true" />
                    )}
                  </div>
                  <div>
                    <strong>{feedback.is_correct ? 'Correct.' : 'Not quite — this is useful information.'}</strong>
                    <br />
                    <DisplayMath children={feedback.explanation} />
                    {feedback.step_note && (
                      <>
                        <br />
                        <span className="text-sm">
                          <DisplayMath children={feedback.step_note} />
                        </span>
                      </>
                    )}
                    {feedback.misconception_id && (
                      <>
                        <br />
                        <span className="text-sm text-amber-700">
                          This response is consistent with: <strong>{getMisconceptionLabel(feedback.misconception_id)}</strong>
                        </span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            )}

            <div className="actions">
              {!submitted ? (
                <button
                  type="submit"
                  className="btn primary"
                  disabled={selectedOption === null && selectedOption !== ''}
                  id="answer-submit"
                >
                  Check answer
                </button>
              ) : showNext ? (
                <button
                  type="button"
                  className="btn primary"
                  onClick={handleNext}
                  id="answer-continue"
                >
                  {question.step_index < question.total_steps - 1 ? 'Next question →' : 'Continue →'}
                </button>
              ) : (
                <Loader2 className="w-5 h-5 animate-spin text-navy" aria-hidden="true" />
              )}
            </div>
          </form>
        </div>
      </div>
    </section>
  )
}

const LEVEL_INFO: Record<number, { name: string }> = {
  1: { name: 'Foundations' },
  2: { name: 'Expressions' },
  3: { name: 'Algebra Essentials' },
  4: { name: 'Equation Solver' },
  5: { name: 'Challenge Lab' },
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