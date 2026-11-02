import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react'

type ToastVariant = 'default' | 'success' | 'error'

interface Toast {
  id: number
  title: string
  message?: string
  variant: ToastVariant
}

interface ToastContextValue {
  push: (toast: { title: string; message?: string; variant?: ToastVariant }) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 1

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const remove = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id))
  }, [])

  const push = useCallback(
    ({ title, message, variant = 'default' }: { title: string; message?: string; variant?: ToastVariant }) => {
      const id = nextId++
      setToasts((current) => [...current, { id, title, message, variant }])
      window.setTimeout(() => remove(id), variant === 'error' ? 7000 : 4500)
    },
    [remove],
  )

  const value = useMemo(() => ({ push }), [push])

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast-item ${toast.variant}`}>
            <span style={{ marginTop: 1, flex: 'none' }}>
              {toast.variant === 'success' ? (
                <CheckCircle2 size={15} />
              ) : toast.variant === 'error' ? (
                <AlertTriangle size={15} />
              ) : (
                <Info size={15} />
              )}
            </span>
            <div style={{ flex: 1 }}>
              <div className="toast-title">{toast.title}</div>
              {toast.message && <div className="toast-message">{toast.message}</div>}
            </div>
            <button
              type="button"
              onClick={() => remove(toast.id)}
              aria-label="Dismiss notification"
              style={{ background: 'transparent', border: 0, color: 'rgba(255,255,255,0.6)', padding: 0 }}
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) throw new Error('useToast must be used inside ToastProvider')
  return context
}
