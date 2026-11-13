// Toast context + hook, kept apart from the <ToastProvider> component
// so the provider file only exports a component (fast-refresh rule).
// Pages import useToast from here; App.jsx mounts the provider from
// ./Toasts.jsx. See Toasts.jsx for what toasts are and when to use them.
import { createContext, useContext } from 'react'

export const ToastContext = createContext(null)

export function useToast() {
  const toast = useContext(ToastContext)
  if (!toast) throw new Error('useToast must be used inside <ToastProvider>')
  return toast
}
