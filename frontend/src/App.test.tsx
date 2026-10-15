import { render, screen, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Dashboard } from '../pages/Dashboard'
import { MathDisplay } from '../components/MathDisplay'
import { api } from '../api/client'

// Mock API
jest.mock('../api/client', () => ({
  api: {
    getSummary: jest.fn(),
    getLevels: jest.fn(),
  },
}))

const mockQueryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: false },
  },
})

function renderWithProviders(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={mockQueryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('MathDisplay', () => {
  it('renders inline math', () => {
    renderWithProviders(<MathDisplay children="x^2" />)
    // KaTeX renders to a span with katex class
    expect(screen.getByText('x^2')).toBeInTheDocument()
  })

  it('renders display math', () => {
    renderWithProviders(<MathDisplay children="\\frac{a}{b}" displayMode />)
    expect(screen.getByText('a/b')).toBeInTheDocument()
  })
})

describe('Dashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('shows loading skeleton when no learner', () => {
    api.getSummary.mockResolvedValue(null)
    api.getLevels.mockResolvedValue({ levels: [] })
    
    renderWithProviders(<Dashboard />)
    expect(screen.getByTestId('skeleton')).toBeInTheDocument()
  })
})

// Simple test to verify test setup works
describe('Test setup', () => {
  it('runs', () => {
    expect(true).toBe(true)
  })
})