import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Pencil, Plus, Search, Users } from 'lucide-react'
import { Async, Avatar, Button, EmptyState, PageHeader, Pagination, Panel, StatusBadge } from '../components/ui.jsx'
import { useAsync, useDebounced } from '../hooks/useAsync.js'
import { formatDate } from '../lib/format.js'
import { api } from '../services/api.js'

const PAGE_SIZE = 10

export default function Employees() {
  const [params, setParams] = useSearchParams()
  const department = params.get('department') || ''
  const status = params.get('status') || ''
  const page = Number(params.get('page') || 1)
  const [search, setSearch] = useState(params.get('q') || '')
  const q = useDebounced(search.trim())

  const setParam = (changes) => {
    const next = new URLSearchParams(params)
    Object.entries({ page: '', ...changes }).forEach(([k, v]) => (v ? next.set(k, v) : next.delete(k)))
    setParams(next, { replace: true })
  }

  // Apply the debounced search text to the URL (and reset to page 1).
  useEffect(() => {
    if ((params.get('q') || '') !== q) setParam({ q })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [q])

  const depts = useAsync(() => api.departments(), [])
  const state = useAsync(
    () => api.listEmployees({ q: params.get('q') || '', department, status, page, page_size: PAGE_SIZE }),
    [params.get('q'), department, status, page],
  )
  const filtered = Boolean(params.get('q') || department || status)

  return (
    <>
      <PageHeader title="Employees" subtitle="Everyone in the company. Adding someone creates their onboarding checklist automatically."
        actions={<Link to="/employees/new"><Button><Plus size={16} aria-hidden="true" /> Add employee</Button></Link>} />

      <Panel padded={false}>
        <form role="search" onSubmit={(e) => e.preventDefault()} className="grid gap-3 border-b border-line p-4 sm:grid-cols-[1fr_200px_160px]">
          <label className="relative block">
            <span className="sr-only">Search employees by name, email or designation</span>
            <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" aria-hidden="true" />
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search name, email or designation"
                   className="block w-full rounded-lg border border-line-strong bg-panel py-2.5 pl-9 pr-3 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25" />
          </label>
          <label>
            <span className="sr-only">Department</span>
            <select value={department} onChange={(e) => setParam({ department: e.target.value })}
                    className="block w-full rounded-lg border border-line-strong bg-panel px-3 py-2.5 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25">
              <option value="">All departments</option>
              {(depts.data || []).map((d) => <option key={d}>{d}</option>)}
            </select>
          </label>
          <label>
            <span className="sr-only">Employment status</span>
            <select value={status} onChange={(e) => setParam({ status: e.target.value })}
                    className="block w-full rounded-lg border border-line-strong bg-panel px-3 py-2.5 text-sm focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-600/25">
              <option value="">Any status</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
        </form>

        <Async state={state}
          empty={(d) => d.items.length === 0 && (
            <EmptyState icon={Users} title={filtered ? 'No employees match these filters' : 'No employees yet'}
              message={filtered ? 'Try a different search or clear the filters.' : 'Add the first employee to get started.'}
              action={filtered
                ? <Button variant="secondary" onClick={() => { setSearch(''); setParams({}, { replace: true }) }}>Clear filters</Button>
                : <Link to="/employees/new"><Button>Add employee</Button></Link>} />
          )}>
          {(d) => (
            <>
              <div className="relative overflow-x-auto">
                <table className="w-full min-w-[640px] text-left text-sm">
                  <caption className="sr-only">Employee directory</caption>
                  <thead className="border-b border-line bg-canvas text-ink-soft">
                    <tr>
                      <th scope="col" className="px-5 py-3 font-semibold">Employee</th>
                      <th scope="col" className="px-3 py-3 font-semibold">Department</th>
                      <th scope="col" className="hidden px-3 py-3 font-semibold md:table-cell">Joined</th>
                      <th scope="col" className="px-3 py-3 font-semibold">Status</th>
                      <th scope="col" className="px-5 py-3 text-right font-semibold"><span className="sr-only">Actions</span></th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {d.items.map((e) => (
                      <tr key={e.id} className="hover:bg-canvas/70">
                        <td className="px-5 py-3">
                          <Link to={`/employees/${e.id}`} className="flex items-center gap-3 rounded">
                            <Avatar name={e.full_name} />
                            <span className="min-w-0">
                              <span className="block truncate font-semibold text-ink hover:underline">{e.full_name}</span>
                              <span className="block truncate text-ink-soft">{e.designation} · {e.email}</span>
                            </span>
                          </Link>
                        </td>
                        <td className="px-3 py-3">{e.department}</td>
                        <td className="hidden whitespace-nowrap px-3 py-3 text-ink-soft md:table-cell">{formatDate(e.joining_date)}</td>
                        <td className="px-3 py-3"><StatusBadge status={e.status} /></td>
                        <td className="px-5 py-3 text-right">
                          <Link to={`/employees/${e.id}/edit`} aria-label={`Edit ${e.full_name}`} className="inline-grid h-9 w-9 place-items-center rounded-lg text-ink-soft hover:bg-black/5 hover:text-ink">
                            <Pencil size={16} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <Pagination page={d.page} pages={d.pages} total={d.total} pageSize={d.page_size} onChange={(p) => setParam({ page: String(p) })} />
            </>
          )}
        </Async>
      </Panel>
    </>
  )
}
