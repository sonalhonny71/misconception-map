import { Link } from 'react-router-dom'
import { Home, RotateCcw } from 'lucide-react'

export function NotFound() {
  return (
    <section className="view active" style={{ minHeight: '60vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '40px 20px' }}>
      <div className="text-8xl font-bold text-lavender mb-4" style={{ fontFamily: '"Plus Jakarta Sans", sans-serif' }}>404</div>
      <h1 className="h1 mb-4">Page not found</h1>
      <p className="text-muted mb-8 max-w-md">The page you're looking for doesn't exist or has been moved. Let's get you back on track.</p>
      <div className="actions">
        <Link to="/" className="btn primary">
          <Home className="mr-2 w-5 h-5" aria-hidden="true" />
          Back to dashboard
        </Link>
        <button className="btn secondary" onClick={() => window.history.back()}>
          <RotateCcw className="mr-2 w-5 h-5" aria-hidden="true" />
          Go back
        </button>
      </div>
    </section>
  )
}