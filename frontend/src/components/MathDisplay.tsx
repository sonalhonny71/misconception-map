import { useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import { splitMathText } from '../lib/mathText'

interface MathDisplayProps {
  children: string
  displayMode?: boolean
  className?: string
}

function renderMath(value: string, target: HTMLElement, displayMode: boolean) {
  try {
    katex.render(value, target, {
      displayMode,
      throwOnError: false,
      strict: false,
      trust: false,
    })
  } catch (e) {
    console.warn('KaTeX render error:', e)
    target.textContent = value
  }
}

export function MathDisplay({ children, displayMode = false, className = '' }: MathDisplayProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const container = ref.current
    if (!container) return
    container.textContent = ''

    const segments = splitMathText(children)

    // Only maths: let KaTeX do all the work (and honour display mode)
    if (segments.length === 1 && segments[0].type === 'math') {
      renderMath(segments[0].value, container, displayMode)
      return
    }

    // Sentences with maths inside: plain words as normal text (so they wrap and keep
    // their spaces), each maths piece rendered inline by KaTeX
    segments.forEach((segment, index) => {
      if (index > 0) container.appendChild(document.createTextNode(' '))
      if (segment.type === 'text') {
        container.appendChild(document.createTextNode(segment.value))
      } else {
        const span = document.createElement('span')
        container.appendChild(span)
        renderMath(segment.value, span, false)
      }
    })
  }, [children, displayMode])

  return <div ref={ref} className={`katex-render ${className}`} />
}

export function InlineMath({ children, className = '' }: { children: string; className?: string }) {
  return <MathDisplay children={children} displayMode={false} className={className} />
}

export function DisplayMath({ children, className = '' }: { children: string; className?: string }) {
  return <MathDisplay children={children} displayMode={true} className={`my-2 ${className}`} />
}
