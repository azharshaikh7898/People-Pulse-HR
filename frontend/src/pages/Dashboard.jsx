import { Link } from 'react-router-dom'
import { ArrowRight } from 'lucide-react'
import { Donut, BarList, StackedBar, SERIES } from '../components/charts.jsx'
import { Async, Avatar, EmptyState, PageHeader, Panel, ProgressBar, StatusBadge } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useAsync } from '../hooks/useAsync.js'
import { categoryLabel, formatDate, formatRange, leaveTypeLabel, timeAgo } from '../lib/format.js'
import { api } from '../services/api.js'

export default function Dashboard() {
  const { isHr, user } = useAuth()
  return isHr ? <HrDashboard /> : <EmployeeDashboard name={user.display_name} />
}

/* ---------------- HR ---------------- */
function HrDashboard() {
  const state = useAsync(() => api.dashboard(), [])
  return (
    <Async state={state}>
      {(d) => {
        const open = d.onboarding.pending + d.onboarding.in_progress
        return (
          <>
            <PageHeader
              title="Dashboard"
              subtitle={`${d.total_active_employees} ${d.total_active_employees === 1 ? 'person is' : 'people are'} active. ${d.onboarding.employees_onboarding} still ${d.onboarding.employees_onboarding === 1 ? 'has' : 'have'} onboarding tasks to finish and ${d.leaves.pending} leave ${d.leaves.pending === 1 ? 'request is' : 'requests are'} waiting for review.`}
            />

            <Panel title="Onboarding progress" className="mb-6"
              action={<Link to="/onboarding" className="inline-flex items-center gap-1 text-sm font-semibold text-brand-600 hover:underline">Manage tasks <ArrowRight size={14} aria-hidden="true" /></Link>}>
              <StackedBar label="Onboarding tasks" segments={[
                { label: 'Completed', value: d.onboarding.completed, color: SERIES.completed },
                { label: 'In progress', value: d.onboarding.in_progress, color: SERIES.in_progress },
                { label: 'Pending', value: d.onboarding.pending, color: SERIES.pending },
              ]} />
              <p className="mt-3 text-sm text-ink-soft">{open} of {d.onboarding.total} tasks are still open across {d.onboarding.employees_onboarding} employees.</p>
            </Panel>

            <dl className="mb-6 grid grid-cols-2 overflow-hidden rounded-xl border border-line bg-panel sm:grid-cols-4">
              <Metric label="Active employees" value={d.total_active_employees} to="/employees?status=active" />
              <Metric label="Leave awaiting review" value={d.leaves.pending} to="/leave?status=pending" tone="warn" />
              <Metric label="Open onboarding tasks" value={open} to="/onboarding" />
              <Metric label="Inactive employees" value={d.total_inactive_employees} to="/employees?status=inactive" />
            </dl>

            <div className="mb-6 grid gap-6 lg:grid-cols-2">
              <Panel title="Employees by department">
                {d.departments.length ? <BarList items={d.departments.map((x) => ({ label: x.department, value: x.count }))} /> : <EmptyState title="No employees yet" />}
              </Panel>
              <Panel title="Leave requests by outcome">
                <Donut centerLabel="requests" segments={[
                  { label: 'Pending', value: d.leaves.pending, color: SERIES.pending },
                  { label: 'Approved', value: d.leaves.approved, color: SERIES.approved },
                  { label: 'Rejected', value: d.leaves.rejected, color: SERIES.rejected },
                ]} />
              </Panel>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <Panel title="Recently added" padded={false}>
                {d.recent_employees.length === 0 ? <EmptyState title="No employees yet" /> : (
                  <ul className="divide-y divide-line">
                    {d.recent_employees.map((e) => (
                      <li key={e.id}>
                        <Link to={`/employees/${e.id}`} className="flex items-center gap-3 px-5 py-3 hover:bg-canvas">
                          <Avatar name={e.full_name} />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate font-semibold">{e.full_name}</span>
                            <span className="block truncate text-sm text-ink-soft">{e.designation}, {e.department}</span>
                          </span>
                          <span className="text-xs text-ink-faint">{timeAgo(e.created_at)}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
              <Panel title="Recent leave requests" padded={false}
                action={<Link to="/leave" className="text-sm font-semibold text-brand-600 hover:underline">View all</Link>}>
                {d.recent_leaves.length === 0 ? <EmptyState title="No leave requests yet" /> : (
                  <ul className="divide-y divide-line">
                    {d.recent_leaves.map((l) => (
                      <li key={l.id} className="flex items-center gap-3 px-5 py-3">
                        <span className="min-w-0 flex-1">
                          <span className="block truncate font-semibold">{l.employee_name}</span>
                          <span className="block truncate text-sm text-ink-soft">{leaveTypeLabel(l.leave_type)}, {formatRange(l.start_date, l.end_date)} ({l.days}d)</span>
                        </span>
                        <StatusBadge status={l.status} />
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          </>
        )
      }}
    </Async>
  )
}

function Metric({ label, value, to, tone }) {
  return (
    <Link to={to} className="block border-line p-5 hover:bg-canvas border-b [&:nth-child(odd)]:border-r [&:nth-child(n+3)]:border-b-0 sm:border-b-0 sm:border-r sm:last:border-r-0">
      <dt className="text-sm text-ink-soft">{label}</dt>
      <dd className={`mt-1 font-display text-3xl font-bold tabular-nums ${tone === 'warn' && value > 0 ? 'text-saffron-700' : ''}`}>{value}</dd>
    </Link>
  )
}

/* ---------------- Employee ---------------- */
function EmployeeDashboard({ name }) {
  const state = useAsync(async () => {
    const [balance, progress, tasks, leaves] = await Promise.all([
      api.leaveBalance(), api.onboardingProgress(), api.onboardingTasks(), api.listLeaves({ page_size: 5 }),
    ])
    return { balance, progress: progress[0], tasks, leaves }
  }, [])

  return (
    <>
      <PageHeader title={`Hello, ${name.split(' ')[0]}`} subtitle="Here is where your leave and onboarding stand today." />
      <Async state={state}>
        {({ balance, progress, tasks, leaves }) => {
          const next = tasks.filter((t) => t.status !== 'completed').slice(0, 4)
          return (
            <div className="grid gap-6 lg:grid-cols-2">
              <Panel title={`Leave balance for ${balance.year}`}
                action={<Link to="/leave" className="text-sm font-semibold text-brand-600 hover:underline">Request leave</Link>}>
                <ul className="space-y-4">
                  {balance.balances.filter((b) => b.allowance !== null).map((b) => (
                    <li key={b.leave_type}>
                      <div className="mb-1 flex justify-between text-sm">
                        <span className="font-medium">{leaveTypeLabel(b.leave_type)}</span>
                        <span className="tabular-nums text-ink-soft"><strong className="text-ink">{b.remaining}</strong> of {b.allowance} days left</span>
                      </div>
                      <ProgressBar percent={Math.round(((b.allowance - b.remaining) / b.allowance) * 100)} label={`${leaveTypeLabel(b.leave_type)} used`} />
                    </li>
                  ))}
                </ul>
              </Panel>

              <Panel title="Your onboarding" action={<Link to="/onboarding" className="text-sm font-semibold text-brand-600 hover:underline">Open checklist</Link>}>
                {progress ? (
                  <>
                    <div className="mb-1 flex justify-between text-sm"><span>{progress.completed} of {progress.total} tasks done</span><strong>{progress.percent}%</strong></div>
                    <ProgressBar percent={progress.percent} label="Onboarding progress" tone={progress.percent === 100 ? 'ok' : 'brand'} />
                    {next.length > 0 ? (
                      <ul className="mt-4 space-y-2">
                        {next.map((t) => (
                          <li key={t.id} className="flex items-start justify-between gap-3 text-sm">
                            <span><span className="font-medium">{t.title}</span><span className="block text-xs text-ink-faint">{categoryLabel(t.category)} · due {formatDate(t.due_date)}</span></span>
                            <StatusBadge status={t.status} />
                          </li>
                        ))}
                      </ul>
                    ) : <p className="mt-4 text-sm text-ok-700">All onboarding tasks are complete.</p>}
                  </>
                ) : <p className="text-sm text-ink-soft">No onboarding tasks assigned.</p>}
              </Panel>

              <Panel title="Your recent leave requests" className="lg:col-span-2" padded={false}>
                {leaves.items.length === 0 ? <EmptyState title="No leave requests yet" message="When you request time off it will show up here." /> : (
                  <ul className="divide-y divide-line">
                    {leaves.items.map((l) => (
                      <li key={l.id} className="flex items-center justify-between gap-3 px-5 py-3">
                        <span><span className="font-semibold">{leaveTypeLabel(l.leave_type)}</span><span className="block text-sm text-ink-soft">{formatRange(l.start_date, l.end_date)} ({l.days} working days)</span></span>
                        <StatusBadge status={l.status} />
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          )
        }}
      </Async>
    </>
  )
}
