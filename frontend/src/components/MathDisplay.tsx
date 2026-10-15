import { useEffect, useRef } from 'react'
import katex from 'katex'
import 'katex/dist/katex.min.css'

interface MathDisplayProps {
  children: string
  displayMode?: boolean
  className?: string
}

export function MathDisplay({ children, displayMode = false, className = '' }: MathDisplayProps) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (ref.current) {
      try {
        katex.render(children, ref.current, {
          displayMode,
          throwOnError: false,
          strict: false,
          trust: false,
        })
      } catch (e) {
        console.warn('KaTeX render error:', e)
        ref.current.textContent = children
      }
    }
  }, [children, displayMode])

  return <div ref={ref} className={`katex-render ${className}`} />
}

export function InlineMath({ children }: { children: string }) {
  return <MathDisplay children={children} displayMode={false} />
}

export function DisplayMath({ children }: { children: string }) {
  return <MathDisplay children={children} displayMode={true} className="my-2" />
}