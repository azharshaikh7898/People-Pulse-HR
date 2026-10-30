import { useState } from 'react'
import { AlertCircle } from 'lucide-react'
import { StatusBadge } from './ui.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { categoryLabel, formatDate, TASK_STATUSES, todayISO } from '../lib/format.js'
import { api } from '../services/api.js'

// One onboarding task with an accessible status dropdown. Calls onChanged() after a successful update.
export function TaskRow({ task, showEmployee = false, onChanged }) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)
  const overdue = task.status !== 'completed' && task.due_date < todayISO()

  async function change(e) {
    const next = e.target.value // read it now: the controlled select resets while we await the API
    setBusy(true)
    try {
      await api.updateTask(task.id, next)
      toast.success(`"${task.title}" marked ${next.replace('_', ' ')}`)
      onChanged?.()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className="flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-3.5">
      <div className="min-w-0 flex-1 basis-64">
        <p className={`font-semibold ${task.status === 'completed' ? 'text-ink-soft line-through decoration-ink-faint' : ''}`}>{task.title}</p>
        <p className="text-sm text-ink-soft">{task.description}</p>
        <p className="mt-1 flex flex-wrap items-center gap-x-3 text-xs text-ink-faint">
          {showEmployee && <span className="font-semibold text-ink-soft">{task.employee_name}</span>}
          <span>{categoryLabel(task.category)}</span>
          <span className={overdue ? 'inline-flex items-center gap-1 font-semibold text-bad-700' : ''}>
            {overdue && <AlertCircle size={12} aria-hidden="true" />}Due {formatDate(task.due_date)}{overdue && ' (overdue)'}
          </span>
        </p>
      </div>
      <StatusBadge status={task.status} />
      <label className="flex items-center gap-2 text-sm">
        <span className="sr-only">Status for {task.title}</span>
        <select value={task.status} onChange={change} disabled={busy}
                className="rounded-lg border border-line-strong bg-panel px-2.5 py-1.5 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25 disabled:opacity-60">
          {TASK_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </label>
    </li>
  )
}
