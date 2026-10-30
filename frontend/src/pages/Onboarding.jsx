import { useMemo, useState } from 'react'
import { ClipboardCheck } from 'lucide-react'
import { TaskRow } from '../components/TaskList.jsx'
import { Async, Avatar, EmptyState, PageHeader, Panel, ProgressBar, Button } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useAsync } from '../hooks/useAsync.js'
import { TASK_CATEGORIES, categoryLabel } from '../lib/format.js'
import { api } from '../services/api.js'

const STATUS_FILTERS = [
  { value: 'open', label: 'Open tasks' }, { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In progress' }, { value: 'completed', label: 'Completed' }, { value: 'all', label: 'All' },
]
const SHOW_STEP = 20

export default function Onboarding() {
  const { isHr } = useAuth()
  const [employeeId, setEmployeeId] = useState('')
  const [category, setCategory] = useState('')
  const [status, setStatus] = useState('open')
  const [showDone, setShowDone] = useState(false)
  const [limit, setLimit] = useState(SHOW_STEP)

  const progress = useAsync(() => api.onboardingProgress(), [])
  const tasks = useAsync(() => api.onboardingTasks({ employee_id: employeeId, category }), [employeeId, category])
  const refresh = () => { progress.reload(); tasks.reload() }

  const visible = useMemo(() => {
    const all = tasks.data || []
    return all.filter((t) => status === 'all' || (status === 'open' ? t.status !== 'completed' : t.status === status))
  }, [tasks.data, status])

  return (
    <>
      <PageHeader title="Onboarding"
        subtitle={isHr ? 'Tasks are created automatically when an employee is added. Track progress and update task status here.' : 'Your checklist for getting set up. Update a task as you go.'} />

      {isHr && (
        <Panel title="Progress by employee" className="mb-6"
          action={<Button variant="ghost" size="sm" aria-pressed={showDone} onClick={() => setShowDone(!showDone)}>{showDone ? 'Hide completed' : 'Show completed'}</Button>}>
          <Async state={progress} empty={(p) => p.length === 0 && <EmptyState icon={ClipboardCheck} title="No onboarding tasks yet" message="Add an employee and their checklist appears here." />}>
            {(rows) => {
              const shown = rows.filter((r) => showDone || r.percent < 100)
              if (shown.length === 0) return <EmptyState icon={ClipboardCheck} title="Everyone has finished onboarding" message="Use “Show completed” to see the full list." />
              return (
                <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {shown.map((r) => (
                    <li key={r.employee_id}>
                      <button type="button" aria-pressed={String(r.employee_id) === employeeId}
                              onClick={() => { setEmployeeId(String(r.employee_id) === employeeId ? '' : String(r.employee_id)); setLimit(SHOW_STEP) }}
                              className={`w-full rounded-lg border p-3 text-left transition-colors ${String(r.employee_id) === employeeId ? 'border-brand-600 bg-brand-50' : 'border-line hover:bg-canvas'}`}>
                        <span className="mb-2 flex items-center gap-2.5">
                          <Avatar name={r.employee_name} size={30} />
                          <span className="min-w-0"><span className="block truncate text-sm font-semibold">{r.employee_name}</span><span className="block truncate text-xs text-ink-soft">{r.department}</span></span>
                          <strong className="ml-auto text-sm tabular-nums">{r.percent}%</strong>
                        </span>
                        <ProgressBar percent={r.percent} label={`${r.employee_name} onboarding progress`} tone={r.percent === 100 ? 'ok' : 'brand'} />
                        <span className="mt-1.5 block text-xs text-ink-faint">{r.completed} of {r.total} done · {r.in_progress} in progress</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )
            }}
          </Async>
        </Panel>
      )}

      <Panel title={isHr ? 'Tasks' : 'Your tasks'} padded={false}>
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4 text-sm">
          <label className="flex items-center gap-2"><span className="font-semibold">Status</span>
            <select value={status} onChange={(e) => { setStatus(e.target.value); setLimit(SHOW_STEP) }} className="rounded-lg border border-line-strong bg-panel px-3 py-2 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25">
              {STATUS_FILTERS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </label>
          <label className="flex items-center gap-2"><span className="font-semibold">Category</span>
            <select value={category} onChange={(e) => { setCategory(e.target.value); setLimit(SHOW_STEP) }} className="rounded-lg border border-line-strong bg-panel px-3 py-2 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25">
              <option value="">All categories</option>
              {TASK_CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </label>
          {isHr && employeeId && <Button variant="secondary" size="sm" onClick={() => setEmployeeId('')}>Show everyone</Button>}
        </div>

        <Async state={tasks}>
          {() => visible.length === 0 ? (
            <EmptyState icon={ClipboardCheck} title={status === 'open' ? 'No open tasks' : 'No tasks match these filters'}
              message={status === 'open' ? 'Everything in this view is complete.' : 'Try a different status or category.'} />
          ) : isHr ? (
            <>
              <ul className="divide-y divide-line">{visible.slice(0, limit).map((t) => <TaskRow key={t.id} task={t} showEmployee onChanged={refresh} />)}</ul>
              {visible.length > limit && (
                <div className="border-t border-line p-4 text-center">
                  <Button variant="secondary" onClick={() => setLimit(limit + SHOW_STEP)}>Show {Math.min(SHOW_STEP, visible.length - limit)} more ({visible.length - limit} remaining)</Button>
                </div>
              )}
            </>
          ) : (
            TASK_CATEGORIES.map((c) => {
              const group = visible.filter((t) => t.category === c.value)
              if (!group.length) return null
              return (
                <section key={c.value} aria-labelledby={`cat-${c.value}`}>
                  <h3 id={`cat-${c.value}`} className="border-b border-line bg-canvas px-5 py-2 text-sm font-bold text-ink-soft">{categoryLabel(c.value)}</h3>
                  <ul className="divide-y divide-line">{group.map((t) => <TaskRow key={t.id} task={t} onChanged={refresh} />)}</ul>
                </section>
              )
            })
          )}
        </Async>
      </Panel>
    </>
  )
}
