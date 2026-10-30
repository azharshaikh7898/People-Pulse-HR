import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, Pencil, UserCheck, UserX } from 'lucide-react'
import { ConfirmDialog } from '../components/Modal.jsx'
import { TaskRow } from '../components/TaskList.jsx'
import { Async, Avatar, Button, EmptyState, PageHeader, Panel, ProgressBar, StatusBadge } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { useAsync } from '../hooks/useAsync.js'
import { formatDate, formatRange, leaveTypeLabel } from '../lib/format.js'
import { api } from '../services/api.js'

export default function EmployeeDetails() {
  const { id } = useParams()
  const { isHr, user } = useAuth()
  const toast = useToast()
  const [confirm, setConfirm] = useState(false)
  const [busy, setBusy] = useState(false)

  const emp = useAsync(() => api.getEmployee(id), [id])
  const tasks = useAsync(() => api.onboardingTasks({ employee_id: id }), [id])
  const leaves = useAsync(() => api.listLeaves({ employee_id: id, page_size: 5 }), [id])
  const balance = useAsync(() => api.leaveBalance({ employee_id: id }), [id])
  const refreshOnboarding = () => { tasks.reload(); emp.reload() }

  async function toggleStatus() {
    setBusy(true)
    try {
      const activating = emp.data.status === 'inactive'
      await (activating ? api.activateEmployee(id) : api.deactivateEmployee(id))
      toast.success(`${emp.data.full_name} was ${activating ? 'reactivated' : 'deactivated'}`)
      setConfirm(false)
      emp.reload()
    } catch (err) {
      toast.error(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {isHr && <Link to="/employees" className="mb-4 inline-flex items-center gap-1 text-sm font-semibold text-brand-600 hover:underline"><ArrowLeft size={14} aria-hidden="true" /> All employees</Link>}
      <Async state={emp}>
        {(e) => {
          const isSelf = user.employee_id === e.id
          return (
            <>
              <PageHeader
                title={e.full_name}
                subtitle={`${e.designation}, ${e.department}`}
                actions={isHr && (
                  <>
                    <Link to={`/employees/${e.id}/edit`}><Button variant="secondary"><Pencil size={16} aria-hidden="true" /> Edit</Button></Link>
                    {!isSelf && (e.status === 'active'
                      ? <Button variant="danger" onClick={() => setConfirm(true)}><UserX size={16} aria-hidden="true" /> Deactivate</Button>
                      : <Button onClick={() => setConfirm(true)}><UserCheck size={16} aria-hidden="true" /> Reactivate</Button>)}
                  </>
                )}
              />

              <div className="mb-6 grid gap-6 lg:grid-cols-3">
                <Panel title="Details" className="lg:col-span-2">
                  <div className="mb-5 flex items-center gap-4"><Avatar name={e.full_name} size={56} /><StatusBadge status={e.status} /></div>
                  <dl className="grid gap-x-8 gap-y-4 sm:grid-cols-2">
                    {[['Email', e.email], ['Department', e.department], ['Designation', e.designation], ['Joined', formatDate(e.joining_date)],
                      ['Can sign in', e.has_login ? 'Yes' : 'No login account']].map(([k, v]) => (
                      <div key={k}><dt className="text-sm text-ink-soft">{k}</dt><dd className="font-semibold">{v}</dd></div>
                    ))}
                  </dl>
                </Panel>
                <Panel title="Leave balance">
                  <Async state={balance}>
                    {(b) => (
                      <ul className="space-y-3 text-sm">
                        {b.balances.filter((x) => x.allowance !== null).map((x) => (
                          <li key={x.leave_type} className="flex justify-between"><span>{leaveTypeLabel(x.leave_type)}</span><span className="tabular-nums"><strong>{x.remaining}</strong> / {x.allowance} left</span></li>
                        ))}
                      </ul>
                    )}
                  </Async>
                </Panel>
              </div>

              <Panel title="Onboarding" className="mb-6" padded={false}
                action={<span className="text-sm text-ink-soft">{e.onboarding.completed} of {e.onboarding.total} complete</span>}>
                <div className="px-5 pt-4"><ProgressBar percent={e.onboarding.percent} label="Onboarding progress" tone={e.onboarding.percent === 100 ? 'ok' : 'brand'} /></div>
                <Async state={tasks} empty={(t) => t.length === 0 && <EmptyState title="No onboarding tasks" />}>
                  {(t) => <ul className="mt-2 divide-y divide-line">{t.map((task) => <TaskRow key={task.id} task={task} onChanged={refreshOnboarding} />)}</ul>}
                </Async>
              </Panel>

              <Panel title="Recent leave requests" padded={false}>
                <Async state={leaves} empty={(l) => l.items.length === 0 && <EmptyState title="No leave requests" />}>
                  {(l) => (
                    <ul className="divide-y divide-line">
                      {l.items.map((r) => (
                        <li key={r.id} className="flex items-center justify-between gap-3 px-5 py-3">
                          <span><span className="font-semibold">{leaveTypeLabel(r.leave_type)}</span><span className="block text-sm text-ink-soft">{formatRange(r.start_date, r.end_date)} ({r.days} working days)</span></span>
                          <StatusBadge status={r.status} />
                        </li>
                      ))}
                    </ul>
                  )}
                </Async>
              </Panel>

              {confirm && (
                <ConfirmDialog
                  title={e.status === 'active' ? `Deactivate ${e.full_name}?` : `Reactivate ${e.full_name}?`}
                  message={e.status === 'active'
                    ? 'They will no longer be able to sign in and will be excluded from active headcount. Their records are kept and you can reactivate them later.'
                    : 'They will be able to sign in again and will count towards active headcount.'}
                  confirmLabel={e.status === 'active' ? 'Deactivate' : 'Reactivate'} danger={e.status === 'active'}
                  loading={busy} onConfirm={toggleStatus} onCancel={() => setConfirm(false)} />
              )}
            </>
          )
        }}
      </Async>
    </>
  )
}
