// Toasts — short confirmations that appear, then dismiss themselves.
//
// WHAT: `ToastProvider` renders a fixed stack (bottom-right on
// desktop, full-width bottom on phones). Pages call
// `const toast = useToast()` then `toast.push('Saved.')` — or
// `toast.push(message, 'error')` for failures. Each toast lives 4.5s,
// has a dismiss button, and is announced via role="status"/"alert".
// WHY: success feedback used to be an inline <p> that pushed content
// around and stayed until the next action. Errors that block a page
// still use the inline .error panel — toasts are for confirmations
// and non-blocking failures only.
// WHERE: frontend/src/components/Toasts.jsx, styles in index.css
// (.toast-stack, .toast). App.jsx mounts one provider for all pages.
import { useCallback, useRef, useState } from 'react'
import { ToastContext } from './toast-context.js'

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(1)

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id))
  }, [])

  const push = useCallback(
    (message, kind = 'success') => {
      const id = nextId.current
      nextId.current += 1
      // Keep the stack short: a burst of actions never floods the screen.
      setToasts((current) => [...current.slice(-2), { id, message, kind }])
      window.setTimeout(() => dismiss(id), 4500)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={{ push, dismiss }}>
      {children}
      {toasts.length > 0 && (
        <div className="toast-stack" aria-live="polite">
          {toasts.map((t) => (
            <div
              key={t.id}
              className={`toast toast-${t.kind}`}
              role={t.kind === 'error' ? 'alert' : 'status'}
            >
              <span>{t.message}</span>
              <button
                type="button"
                className="toast-close"
                onClick={() => dismiss(t.id)}
                aria-label="Dismiss notification"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  )
}
