import { forwardRef, useId } from 'react'
import { AlertTriangle, ChevronLeft, ChevronRight, Inbox, Loader2 } from 'lucide-react'

export function cx(...parts) { return parts.filter(Boolean).join(' ') }

/* ---------- Buttons ---------- */
const BTN = {
  primary: 'bg-brand-600 text-white hover:bg-brand-700 disabled:bg-brand-600/50',
  secondary: 'border border-line-strong bg-panel text-ink hover:bg-canvas disabled:text-ink-faint',
  danger: 'bg-bad-700 text-white hover:bg-[#8a2618] disabled:bg-bad-700/50',
  ghost: 'text-ink-soft hover:bg-black/5 hover:text-ink',
}
export function Button({ variant = 'primary', size = 'md', loading = false, className, children, ...rest }) {
  return (
    <button
      type="button"
      {...rest}
      disabled={rest.disabled || loading}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors disabled:cursor-not-allowed',
        size === 'sm' ? 'px-3 py-1.5 text-sm' : 'px-4 py-2.5 text-sm',
        BTN[variant], className,
      )}
    >
      {loading && <Loader2 size={16} className="spin" aria-hidden="true" />}
      {children}
    </button>
  )
}

/* ---------- Form fields (every input has a visible label) ---------- */
const inputCls = (error) => cx(
  'block w-full rounded-lg border bg-panel px-3 py-2.5 text-sm text-ink placeholder:text-ink-faint',
  'focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25 disabled:bg-canvas disabled:text-ink-faint',
  error ? 'border-bad-700' : 'border-line-strong',
)

function FieldShell({ label, error, hint, id, children, className }) {
  return (
    <div className={className}>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-ink">{label}</label>
      {children}
      {hint && !error && <p id={`${id}-hint`} className="mt-1.5 text-xs text-ink-faint">{hint}</p>}
      {error && <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-bad-700">{error}</p>}
    </div>
  )
}
const describe = (id, error, hint) => (error ? `${id}-error` : hint ? `${id}-hint` : undefined)

export const TextField = forwardRef(function TextField({ label, error, hint, className, ...rest }, ref) {
  const id = useId()
  return (
    <FieldShell label={label} error={error} hint={hint} id={id} className={className}>
      <input ref={ref} id={id} aria-invalid={Boolean(error)} aria-describedby={describe(id, error, hint)} className={inputCls(error)} {...rest} />
    </FieldShell>
  )
})

export function SelectField({ label, error, hint, className, children, ...rest }) {
  const id = useId()
  return (
    <FieldShell label={label} error={error} hint={hint} id={id} className={className}>
      <select id={id} aria-invalid={Boolean(error)} aria-describedby={describe(id, error, hint)} className={inputCls(error)} {...rest}>{children}</select>
    </FieldShell>
  )
}

export function TextAreaField({ label, error, hint, className, ...rest }) {
  const id = useId()
  return (
    <FieldShell label={label} error={error} hint={hint} id={id} className={className}>
      <textarea id={id} rows={3} aria-invalid={Boolean(error)} aria-describedby={describe(id, error, hint)} className={inputCls(error)} {...rest} />
    </FieldShell>
  )
}

/* ---------- Layout bits ---------- */
export function PageHeader({ title, subtitle, actions }) {
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-2xl font-bold text-ink sm:text-3xl">{title}</h1>
        {subtitle && <p className="mt-1 max-w-2xl text-ink-soft">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  )
}

export function Panel({ title, action, children, className, padded = true }) {
  return (
    <section className={cx('min-w-0 rounded-xl border border-line bg-panel', className)}>
      {(title || action) && (
        <header className="flex items-center justify-between gap-3 border-b border-line px-5 py-3.5">
          <h2 className="text-base font-bold">{title}</h2>
          {action}
        </header>
      )}
      <div className={padded ? 'p-5' : ''}>{children}</div>
    </section>
  )
}

/* ---------- Status badges (text + dot, never colour alone) ---------- */
const BADGES = {
  active: ['Active', 'bg-ok-50 text-ok-700', 'bg-ok-700'],
  inactive: ['Inactive', 'bg-canvas text-ink-soft border border-line', 'bg-ink-faint'],
  pending: ['Pending', 'bg-saffron-50 text-saffron-700', 'bg-saffron-500'],
  approved: ['Approved', 'bg-ok-50 text-ok-700', 'bg-ok-700'],
  rejected: ['Rejected', 'bg-bad-50 text-bad-700', 'bg-bad-700'],
  cancelled: ['Cancelled', 'bg-canvas text-ink-soft border border-line', 'bg-ink-faint'],
  in_progress: ['In progress', 'bg-info-50 text-info-700', 'bg-info-700'],
  completed: ['Completed', 'bg-ok-50 text-ok-700', 'bg-ok-700'],
  hr_admin: ['HR administrator', 'bg-brand-50 text-brand-700', 'bg-brand-600'],
  employee: ['Employee', 'bg-canvas text-ink-soft border border-line', 'bg-ink-faint'],
}
export function StatusBadge({ status }) {
  const [label, cls, dot] = BADGES[status] || [status, 'bg-canvas text-ink-soft', 'bg-ink-faint']
  return (
    <span className={cx('inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold', cls)}>
      <span className={cx('h-1.5 w-1.5 rounded-full', dot)} aria-hidden="true" />
      {label}
    </span>
  )
}

/* ---------- Loading / empty / error states ---------- */
export function Spinner({ label = 'Loading' }) {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-12 text-ink-soft">
      <Loader2 size={20} className="spin" aria-hidden="true" />
      <span className="text-sm">{label}…</span>
    </div>
  )
}

export function EmptyState({ title, message, action, icon: Icon = Inbox }) {
  return (
    <div className="flex flex-col items-center px-4 py-12 text-center">
      <span className="mb-3 grid h-11 w-11 place-items-center rounded-full bg-brand-50 text-brand-600"><Icon size={22} aria-hidden="true" /></span>
      <h3 className="text-base font-bold">{title}</h3>
      {message && <p className="mt-1 max-w-sm text-sm text-ink-soft">{message}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }) {
  return (
    <div role="alert" className="flex flex-col items-center px-4 py-12 text-center">
      <span className="mb-3 grid h-11 w-11 place-items-center rounded-full bg-bad-50 text-bad-700"><AlertTriangle size={22} aria-hidden="true" /></span>
      <h3 className="text-base font-bold">Something went wrong</h3>
      <p className="mt-1 max-w-sm text-sm text-ink-soft">{error?.message || 'Please try again.'}</p>
      {onRetry && <Button variant="secondary" className="mt-4" onClick={onRetry}>Try again</Button>}
    </div>
  )
}

/* Shows spinner / error / children, so every page handles all three states the same way. */
export function Async({ state, children, empty }) {
  if (state.loading && !state.data) return <Spinner />
  if (state.error) return <ErrorState error={state.error} onRetry={state.reload} />
  if (empty && empty(state.data)) return empty(state.data)
  return children(state.data)
}

/* ---------- Pagination ---------- */
export function Pagination({ page, pages, total, pageSize, onChange }) {
  if (total === 0) return null
  const from = (page - 1) * pageSize + 1
  const to = Math.min(page * pageSize, total)
  return (
    <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3 text-sm">
      <p className="text-ink-soft" aria-live="polite">Showing {from}–{to} of {total}</p>
      <div className="flex items-center gap-1">
        <Button variant="secondary" size="sm" onClick={() => onChange(page - 1)} disabled={page <= 1} aria-label="Previous page"><ChevronLeft size={16} /></Button>
        <span className="px-2 text-ink-soft">Page {page} of {pages}</span>
        <Button variant="secondary" size="sm" onClick={() => onChange(page + 1)} disabled={page >= pages} aria-label="Next page"><ChevronRight size={16} /></Button>
      </div>
    </nav>
  )
}

export function ProgressBar({ percent, label, tone = 'brand' }) {
  return (
    <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent} aria-label={label}
         className="h-2 w-full overflow-hidden rounded-full bg-line">
      <div className={cx('h-full rounded-full transition-all', tone === 'ok' ? 'bg-ok-700' : 'bg-brand-600')} style={{ width: `${percent}%` }} />
    </div>
  )
}

export function Avatar({ name, size = 36 }) {
  const initials = name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()
  return (
    <span aria-hidden="true" style={{ width: size, height: size, fontSize: size * 0.38 }}
          className="grid shrink-0 place-items-center rounded-full bg-brand-100 font-bold text-brand-700">{initials}</span>
  )
}
