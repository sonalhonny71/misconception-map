import { create } from 'zustand'
import { useEffect } from 'react'

interface ToastState {
  message: string
  type: 'success' | 'error' | 'info'
  visible: boolean
  show: (message: string, type?: 'success' | 'error' | 'info') => void
  hide: () => void
}

export const useToast = create<ToastState>((set) => ({
  message: '',
  type: 'info',
  visible: false,
  show: (message, type = 'info') => set({ message, type, visible: true }),
  hide: () => set({ visible: false }),
}))

export function ToastContainer() {
  const { message, type, visible, hide } = useToast()

  useEffect(() => {
    if (visible) {
      const timer = setTimeout(hide, 4000)
      return () => clearTimeout(timer)
    }
  }, [visible, hide])

  if (!visible) return null

  const bgColors = {
    success: 'bg-teal-600',
    error: 'bg-red-600',
    info: 'bg-navy-900',
  }

  return (
    <div
      className={`toast show ${bgColors[type]} text-white px-5 py-3 rounded-xl shadow-lg flex items-center gap-3 z-50 fixed bottom-6 right-6 max-w-md`}
      role="alert"
      aria-live="polite"
    >
      <span className="flex-1">{message}</span>
      <button onClick={hide} className="text-white/70 hover:text-white text-xl leading-none p-0" aria-label="Dismiss">
        ×
      </button>
    </div>
  )
}