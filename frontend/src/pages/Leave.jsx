import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Check, Plus, X } from 'lucide-react'
import { ConfirmDialog, Modal } from '../components/Modal.jsx'
import { Async, Button, EmptyState, PageHeader, Pagination, Panel, ProgressBar, SelectField, StatusBadge, TextAreaField, TextField } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { useAsync } from '../hooks/useAsync.js'
import { LEAVE_STATUSES, LEAVE_TYPES, formatDate, formatRange, leaveTypeLabel, todayISO, workingDays } from '../lib/format.js'
import { api } from '../services/api.js'

const PAGE_SIZE = 10

export default function Leave() {
  const { isHr, user } = useAuth()
  const toast = useToast()
  const [params, setParams] = useSearchParams()
  const status = params.get('status') || ''
  const scope = isHr ? params.get('scope') || 'all' : 'mine'
  const page = Number(params.get('page') || 1)
  const [requesting, setRequesting] = useState(false)
  const [reviewing, setReviewing] = useState(null)
  const [cancelling, setCancelling] = useState(null)
  const [busy, setBusy] = useState(false)

  const setParam = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries({ page: '', ...changes }).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    setParams(next, { replace: true })
  }

  const list = useAsync(() => api.listLeaves({ status, page, page_size: PAGE_SIZE, mine: isHr && scope === 'mine' ? true : undefined }), [status, scope, page])
  const balance = useAsync(() => (user.employee_id ? api.leaveBalance() : Promise.resolve(null)), [])
  const refresh = () => { list.reload(); balance.reload() }

  async function doCancel() {
    setBusy(true)
    try {
      await api.cancelLeave(cancelling.id)
      toast.success('Leave request cancelled')
      setCancelling(null)
      refresh()
    } catch (err) { toast.error(err.message) } finally { setBusy(false) }
  }

  return (
    <>
      <PageHeader title="Leave"
        subtitle={isHr ? 'Review requests from the team and manage your own time off.' : 'Request time off and track the status of your requests.'}
        actions={user.employee_id && <Button onClick={() => setRequesting(true)}><Plus size={16} aria-hidden="true" /> Request leave</Button>} />

      {balance.data && (
        <Panel title={`Your leave balance, ${balance.data.year}`} className="mb-6">
          <ul className="grid gap-5 sm:grid-cols-3">
            {balance.data.balances.filter((b) => b.allowance !== null).map((b) => (
              <li key={b.leave_type}>
                <div className="mb-1 flex items-baseline justify-between text-sm">
                  <span className="font-semibold">{leaveTypeLabel(b.leave_type)}</span>
                  <span className="text-ink-soft"><strong className="text-lg text-ink">{b.remaining}</strong> / {b.allowance} days</span>
                </div>
                <ProgressBar percent={Math.round(((b.allowance - b.remaining) / b.allowance) * 100)} label={`${leaveTypeLabel(b.leave_type)} used`} />
                <p className="mt-1 text-xs text-ink-faint">{b.used} used · {b.pending} awaiting approval</p>
              </li>
            ))}
          </ul>
        </Panel>
      )}

      <Panel padded={false}>
        <div className="flex flex-wrap items-center gap-3 border-b border-line p-4">
          {isHr && (
            <div role="group" aria-label="Which requests" className="inline-flex rounded-lg border border-line-strong p-0.5 text-sm font-semibold">
              {[['all', 'All requests'], ['mine', 'My requests']].map(([v, l]) => (
                <button key={v} type="button" aria-pressed={scope === v} onClick={() => setParam({ scope: v === 'all' ? '' : v })}
                        className={`rounded-md px-3 py-1.5 ${scope === v ? 'bg-brand-600 text-white' : 'text-ink-soft hover:bg-black/5'}`}>{l}</button>
              ))}
            </div>
          )}
          <label className="flex items-center gap-2 text-sm">
            <span className="font-semibold">Status</span>
            <select value={status} onChange={(e) => setParam({ status: e.target.value })}
                    className="rounded-lg border border-line-strong bg-panel px-3 py-2 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25">
              <option value="">All</option>
              {LEAVE_STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </label>
        </div>

        <Async state={list}
          empty={(d) => d.items.length === 0 && (
            <EmptyState title={status ? `No ${status} requests` : 'No leave requests yet'}
              message={status ? 'Try another status filter.' : 'Requests will appear here once they are submitted.'}
              action={!status && user.employee_id && <Button onClick={() => setRequesting(true)}>Request leave</Button>} />
          )}>
          {(d) => (
            <>
              <div className="relative overflow-x-auto">
                <table className="w-full min-w-[720px] text-left text-sm">
                  <caption className="sr-only">Leave requests</caption>
                  <thead className="border-b border-line bg-canvas text-ink-soft">
                    <tr>
                      {scope === 'all' && <th scope="col" className="px-5 py-3 font-semibold">Employee</th>}
                      <th scope="col" className="px-3 py-3 font-semibold">Type</th>
                      <th scope="col" className="px-3 py-3 font-semibold">Dates</th>
                      <th scope="col" className="px-3 py-3 font-semibold">Days</th>
                      <th scope="col" className="px-3 py-3 font-semibold">Status</th>
                      <th scope="col" className="px-5 py-3 text-right font-semibold">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {d.items.map((l) => {
                      const own = l.employee_id === user.employee_id
                      const canCancel = own && (l.status === 'pending' || (l.status === 'approved' && l.start_date > todayISO()))
                      return (
                        <tr key={l.id} className="align-top hover:bg-canvas/70">
                          {scope === 'all' && <td className="px-5 py-3 font-semibold">{l.employee_name}</td>}
                          <td className="px-3 py-3">
                            {leaveTypeLabel(l.leave_type)}
                            <span className="block max-w-[16rem] truncate text-xs text-ink-faint" title={l.reason}>{l.reason}</span>
                          </td>
                          <td className="whitespace-nowrap px-3 py-3">{formatRange(l.start_date, l.end_date)}</td>
                          <td className="px-3 py-3 tabular-nums">{l.days}</td>
                          <td className="px-3 py-3">
                            <StatusBadge status={l.status} />
                            {l.review_note && <span className="mt-1 block max-w-[12rem] truncate text-xs text-ink-faint" title={l.review_note}>Note: {l.review_note}</span>}
                          </td>
                          <td className="px-5 py-3 text-right">
                            <div className="flex justify-end gap-2">
                              {isHr && l.status === 'pending' && !own && (
                                <Button size="sm" onClick={() => setReviewing(l)} aria-label={`Review request from ${l.employee_name}`}>Review</Button>
                              )}
                              {canCancel && <Button size="sm" variant="secondary" onClick={() => setCancelling(l)} aria-label={`Cancel ${leaveTypeLabel(l.leave_type)} request`}>Cancel</Button>}
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <Pagination page={d.page} pages={d.pages} total={d.total} pageSize={d.page_size} onChange={(p) => setParam({ page: String(p) })} />
            </>
          )}
        </Async>
      </Panel>

      {requesting && <RequestModal onClose={() => setRequesting(false)} onDone={() => { setRequesting(false); refresh() }} />}
      {reviewing && <ReviewModal leave={reviewing} onClose={() => setReviewing(null)} onDone={() => { setReviewing(null); refresh() }} />}
      {cancelling && (
        <ConfirmDialog title="Cancel this request?" danger confirmLabel="Cancel request" loading={busy} onConfirm={doCancel} onCancel={() => setCancelling(null)}
          message={`Your ${leaveTypeLabel(cancelling.leave_type).toLowerCase()} request for ${formatRange(cancelling.start_date, cancelling.end_date)} will be cancelled and the days returned to your balance.`} />
      )}
    </>
  )
}

function RequestModal({ onClose, onDone }) {
  const toast = useToast()
  const [form, setForm] = useState({ leave_type: 'annual', start_date: '', end_date: '', reason: '' })
  const [errors, setErrors] = useState({})
  const [serverError, setServerError] = useState('')
  const [busy, setBusy] = useState(false)
  const days = workingDays(form.start_date, form.end_date)
  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); setErrors({ ...errors, [k]: undefined }); setServerError('') }

  async function submit(e) {
    e.preventDefault()
    const found = {}
    if (!form.start_date) found.start_date = 'Choose a start date'
    if (!form.end_date) found.end_date = 'Choose an end date'
    else if (form.start_date && form.end_date < form.start_date) found.end_date = 'End date cannot be before the start date'
    else if (form.start_date && days === 0) found.end_date = 'These dates only include a weekend'
    if (form.reason.trim().length < 3) found.reason = 'Add a short reason'
    setErrors(found)
    if (Object.keys(found).length) return
    setBusy(true)
    try {
      await api.createLeave({ ...form, reason: form.reason.trim() })
      toast.success('Leave request submitted for approval')
      onDone()
    } catch (err) {
      setServerError(err.message)
      setBusy(false)
    }
  }

  return (
    <Modal title="Request leave" onClose={onClose} footer={
      <>
        <Button variant="secondary" onClick={onClose}>Cancel</Button>
        <Button type="submit" form="leave-form" loading={busy}>Submit request</Button>
      </>
    }>
      <form id="leave-form" onSubmit={submit} noValidate className="space-y-4">
        {serverError && <div role="alert" className="rounded-lg border border-bad-700/30 bg-bad-50 px-4 py-3 text-sm font-medium text-bad-700">{serverError}</div>}
        <SelectField label="Leave type" value={form.leave_type} onChange={set('leave_type')}>
          {LEAVE_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
        </SelectField>
        <div className="grid gap-4 sm:grid-cols-2">
          <TextField label="From" type="date" value={form.start_date} onChange={set('start_date')} error={errors.start_date} data-autofocus />
          <TextField label="To" type="date" value={form.end_date} min={form.start_date || undefined} onChange={set('end_date')} error={errors.end_date} />
        </div>
        {days > 0 && <p className="text-sm font-medium text-brand-700">{days} working {days === 1 ? 'day' : 'days'} (weekends are not counted)</p>}
        <TextAreaField label="Reason" value={form.reason} onChange={set('reason')} error={errors.reason} maxLength={500} />
      </form>
    </Modal>
  )
}

function ReviewModal({ leave, onClose, onDone }) {
  const toast = useToast()
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  async function decide(decision) {
    setBusy(decision)
    setError('')
    try {
      await api.reviewLeave(leave.id, { decision, note: note.trim() || null })
      toast.success(`Request from ${leave.employee_name} ${decision}`)
      onDone()
    } catch (err) { setError(err.message); setBusy('') }
  }

  return (
    <Modal title="Review leave request" onClose={onClose} footer={
      <>
        <Button variant="danger" loading={busy === 'rejected'} disabled={Boolean(busy)} onClick={() => decide('rejected')}><X size={16} aria-hidden="true" /> Reject</Button>
        <Button loading={busy === 'approved'} disabled={Boolean(busy)} onClick={() => decide('approved')}><Check size={16} aria-hidden="true" /> Approve</Button>
      </>
    }>
      <dl className="mb-4 grid grid-cols-2 gap-3 text-sm">
        <div><dt className="text-ink-soft">Employee</dt><dd className="font-semibold">{leave.employee_name}</dd></div>
        <div><dt className="text-ink-soft">Type</dt><dd className="font-semibold">{leaveTypeLabel(leave.leave_type)}</dd></div>
        <div><dt className="text-ink-soft">Dates</dt><dd className="font-semibold">{formatRange(leave.start_date, leave.end_date)}</dd></div>
        <div><dt className="text-ink-soft">Working days</dt><dd className="font-semibold">{leave.days}</dd></div>
        <div className="col-span-2"><dt className="text-ink-soft">Reason</dt><dd>{leave.reason}</dd></div>
        <div className="col-span-2"><dt className="text-ink-soft">Submitted</dt><dd>{formatDate(leave.created_at)}</dd></div>
      </dl>
      {error && <div role="alert" className="mb-3 rounded-lg border border-bad-700/30 bg-bad-50 px-4 py-3 text-sm font-medium text-bad-700">{error}</div>}
      <TextAreaField label="Note to the employee (optional)" value={note} onChange={(e) => setNote(e.target.value)} maxLength={500} />
    </Modal>
  )
}
