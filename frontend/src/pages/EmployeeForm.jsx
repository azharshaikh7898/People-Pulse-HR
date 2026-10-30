import { useEffect, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { Button, Async, PageHeader, Panel, SelectField, TextField } from '../components/ui.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { useAsync } from '../hooks/useAsync.js'
import { api } from '../services/api.js'

const EMPTY = { full_name: '', email: '', department: '', designation: '', joining_date: '', initial_password: '' }
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function validate(f, isEdit) {
  const e = {}
  if (f.full_name.trim().length < 2) e.full_name = 'Enter the full name (at least 2 characters)'
  if (!EMAIL_RE.test(f.email.trim())) e.email = 'Enter a valid email address'
  if (!f.department) e.department = 'Choose a department'
  if (f.designation.trim().length < 2) e.designation = 'Enter a job title'
  if (!f.joining_date) e.joining_date = 'Choose the joining date'
  if (!isEdit && f.initial_password && (f.initial_password.length < 8 || !/[A-Za-z]/.test(f.initial_password) || !/\d/.test(f.initial_password)))
    e.initial_password = 'Use at least 8 characters with a letter and a number'
  return e
}

export default function EmployeeForm() {
  const { id } = useParams()
  const isEdit = Boolean(id)
  const navigate = useNavigate()
  const toast = useToast()
  const departments = useAsync(() => api.departments(), [])
  const existing = useAsync(() => (isEdit ? api.getEmployee(id) : Promise.resolve(null)), [id])
  const [form, setForm] = useState(EMPTY)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (existing.data) {
      const { full_name, email, department, designation, joining_date } = existing.data
      setForm({ ...EMPTY, full_name, email, department, designation, joining_date })
    }
  }, [existing.data])

  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); setErrors({ ...errors, [k]: undefined }) }

  async function submit(ev) {
    ev.preventDefault()
    const found = validate(form, isEdit)
    setErrors(found)
    if (Object.keys(found).length) {
      document.getElementById('form-summary')?.focus()
      return
    }
    setBusy(true)
    const payload = {
      full_name: form.full_name.trim(), email: form.email.trim(), department: form.department,
      designation: form.designation.trim(), joining_date: form.joining_date,
    }
    try {
      let saved
      if (isEdit) {
        saved = await api.updateEmployee(id, payload)
        toast.success(`${saved.full_name} was updated`)
      } else {
        saved = await api.createEmployee({ ...payload, initial_password: form.initial_password || null })
        toast.success(`${saved.full_name} was added with ${saved.onboarding.total} onboarding tasks`)
      }
      navigate(`/employees/${saved.id}`)
    } catch (err) {
      // Map server-side field errors (e.g. duplicate email) onto the inputs.
      const fieldErrs = {}
      err.fieldErrors?.forEach((fe) => { if (fe.field) fieldErrs[fe.field] = fe.message })
      if (err.status === 409) fieldErrs.email = err.message
      setErrors(Object.keys(fieldErrs).length ? fieldErrs : { _form: err.message })
      if (!Object.keys(fieldErrs).length) toast.error(err.message)
      setBusy(false)
    }
  }

  const summary = Object.entries(errors).filter(([, v]) => v)

  return (
    <>
      <PageHeader title={isEdit ? 'Edit employee' : 'Add employee'}
        subtitle={isEdit ? 'Update the details below. Changes apply immediately.' : 'Saving creates the employee and their full onboarding checklist in one step.'} />
      <Async state={existing}>
        {() => (
          <Panel className="max-w-3xl">
            <form onSubmit={submit} noValidate>
              {summary.length > 0 && (
                <div id="form-summary" tabIndex={-1} role="alert" className="mb-5 rounded-lg border border-bad-700/30 bg-bad-50 px-4 py-3 text-sm text-bad-700">
                  <p className="font-semibold">Please fix {summary.length === 1 ? 'this issue' : `these ${summary.length} issues`} before saving:</p>
                  <ul className="mt-1 list-disc pl-5">{summary.map(([k, v]) => <li key={k}>{v}</li>)}</ul>
                </div>
              )}
              <div className="grid gap-5 sm:grid-cols-2">
                <TextField label="Full name" value={form.full_name} onChange={set('full_name')} error={errors.full_name} autoComplete="off" required />
                <TextField label="Work email" type="email" value={form.email} onChange={set('email')} error={errors.email} autoComplete="off" required />
                <SelectField label="Department" value={form.department} onChange={set('department')} error={errors.department} required>
                  <option value="" disabled>Select a department</option>
                  {(departments.data || []).map((d) => <option key={d}>{d}</option>)}
                </SelectField>
                <TextField label="Designation" value={form.designation} onChange={set('designation')} error={errors.designation} placeholder="e.g. Software Engineer" required />
                <TextField label="Joining date" type="date" value={form.joining_date} onChange={set('joining_date')} error={errors.joining_date}
                           hint="Onboarding task due dates are calculated from this date." required />
                {!isEdit && (
                  <TextField label="Temporary password (optional)" type="text" value={form.initial_password} onChange={set('initial_password')}
                             error={errors.initial_password} autoComplete="off" hint="If set, the employee can sign in with their email and this password." />
                )}
              </div>
              <div className="mt-6 flex flex-wrap justify-end gap-2 border-t border-line pt-5">
                <Link to={isEdit ? `/employees/${id}` : '/employees'}><Button variant="secondary">Cancel</Button></Link>
                <Button type="submit" loading={busy}>{isEdit ? 'Save changes' : 'Add employee'}</Button>
              </div>
            </form>
          </Panel>
        )}
      </Async>
    </>
  )
}
