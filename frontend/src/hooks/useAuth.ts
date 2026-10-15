import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'

interface Learner {
  token: string
  tokenHash: string
}

interface AuthState {
  learner: Learner | null
  loading: boolean
  setLearner: (learner: Learner | null) => void
  clearLearner: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      learner: null,
      loading: true,
      setLearner: (learner) => set({ learner, loading: false }),
      clearLearner: () => set({ learner: null, loading: false }),
    }),
    {
      name: 'misconceptionmap-auth',
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        if (state) state.loading = false
      },
    }
  )
)

/** Convenience hook used by App and pages */
export function useAuth() {
  const learner = useAuthStore((s) => s.learner)
  const loading = useAuthStore((s) => s.loading)
  const setLearner = useAuthStore((s) => s.setLearner)
  const clearLearner = useAuthStore((s) => s.clearLearner)
  return { learner, loading, setLearner, clearLearner }
}