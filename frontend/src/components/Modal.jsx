import { useEffect, useId, useRef } from 'react'
import { X } from 'lucide-react'
import { Button } from './ui.jsx'

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

// Accessible dialog: Esc closes, Tab stays inside, focus returns to the opener afterwards.
export function Modal({ title, onClose, children, footer, size = 'md' }) {
  const titleId = useId()
  const ref = useRef(null)

  useEffect(() => {
    const opener = document.activeElement
    const first = ref.current?.querySelector('[data-autofocus]') || ref.current?.querySelector(FOCUSABLE)
    first?.focus()
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function onKey(e) {
      if (e.key === 'Escape') { e.stopPropagation(); onClose() }
      if (e.key !== 'Tab') return
      const items = [...ref.current.querySelectorAll(FOCUSABLE)]
      if (!items.length) return
      const [firstEl, lastEl] = [items[0], items[items.length - 1]]
      if (e.shiftKey && document.activeElement === firstEl) { e.preventDefault(); lastEl.focus() }
      else if (!e.shiftKey && document.activeElement === lastEl) { e.preventDefault(); firstEl.focus() }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = prevOverflow
      opener?.focus?.()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-brand-950/50 p-0 sm:items-center sm:p-4" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div ref={ref} role="dialog" aria-modal="true" aria-labelledby={titleId}
           className={`flex max-h-[92vh] w-full flex-col rounded-t-2xl bg-panel shadow-2xl sm:rounded-2xl ${size === 'lg' ? 'sm:max-w-2xl' : 'sm:max-w-md'}`}>
        <div className="flex items-center justify-between border-b border-line px-5 py-4">
          <h2 id={titleId} className="text-lg font-bold">{title}</h2>
          <button type="button" onClick={onClose} aria-label="Close dialog" className="rounded-md p-1 text-ink-soft hover:bg-black/5"><X size={20} /></button>
        </div>
        <div className="overflow-y-auto px-5 py-4">{children}</div>
        {footer && <div className="flex flex-wrap justify-end gap-2 border-t border-line px-5 py-4">{footer}</div>}
      </div>
    </div>
  )
}

export function ConfirmDialog({ title, message, confirmLabel, danger = false, loading, onConfirm, onCancel }) {
  return (
    <Modal title={title} onClose={onCancel} footer={
      <>
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button variant={danger ? 'danger' : 'primary'} loading={loading} onClick={onConfirm} data-autofocus>{confirmLabel}</Button>
      </>
    }>
      <p className="text-ink-soft">{message}</p>
    </Modal>
  )
}
