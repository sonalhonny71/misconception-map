import { render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { Dashboard } from './pages/Dashboard'
import { MathDisplay } from './components/MathDisplay'
import { useAuthStore } from './hooks/useAuth'

vi.mock('./api/client', () => ({
  ApiError: class ApiError extends Error {},
  api: {
    getSummary: vi.fn().mockResolvedValue({
      total_xp: 0,
      practice_sets_completed: 0,
      latest_retest: null,
      active_level: 3,
    }),
    getLevels: vi.fn().mockResolvedValue({ levels: [] }),
  },
}))

function renderWithProviders(ui: React.ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  )
}

describe('MathDisplay', () => {
  it('renders inline math with KaTeX', () => {
    const { container } = renderWithProviders(<MathDisplay>{'x^2'}</MathDisplay>)
    expect(container.querySelector('.katex')).not.toBeNull()
  })

  it('renders display math with KaTeX', () => {
    const { container } = renderWithProviders(<MathDisplay displayMode>{'\\frac{a}{b}'}</MathDisplay>)
    expect(container.querySelector('.katex-display')).not.toBeNull()
  })
})

describe('Dashboard', () => {
  beforeEach(() => {
    useAuthStore.setState({ learner: null, loading: false })
  })

  it('shows a loading skeleton while there is no learner yet', () => {
    renderWithProviders(<Dashboard />)
    expect(screen.getAllByTestId('skeleton').length).toBeGreaterThan(0)
  })

  it('shows the dashboard once a learner exists', async () => {
    useAuthStore.setState({ learner: { token: 't', tokenHash: 'h' }, loading: false })
    renderWithProviders(<Dashboard />)
    expect(await screen.findByText('Learn from every answer.')).toBeInTheDocument()
  })
})
