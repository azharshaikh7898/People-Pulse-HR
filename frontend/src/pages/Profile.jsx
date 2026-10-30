import { useState } from 'react'
import { Avatar, Async, Button, PageHeader, Panel, StatusBadge, TextField } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { useAsync } from '../hooks/useAsync.js'
import { formatDate } from '../lib/format.js'
import { api } from '../services/api.js'

export default function Profile() {
  const { user } = useAuth()
  const record = useAsync(() => (user.employee_id ? api.getEmployee(user.employee_id) : Promise.resolve(null)), [user.employee_id])

  return (
    <>
      <PageHeader title="Your profile" subtitle="Your account details and password." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="Account">
          <div className="mb-5 flex items-center gap-4">
            <Avatar name={user.display_name} size={56} />
            <div><p className="text-lg font-bold">{user.display_name}</p><StatusBadge status={user.role} /></div>
          </div>
          <Async state={record}>
            {(e) => (
              <dl className="grid gap-4 sm:grid-cols-2">
                <Item k="Sign-in email" v={user.email} />
                {e && <><Item k="Department" v={e.department} /><Item k="Designation" v={e.designation} /><Item k="Joined" v={formatDate(e.joining_date)} /></>}
              </dl>
            )}
          </Async>
        </Panel>
        <PasswordForm />
      </div>
    </>
  )
}

const Item = ({ k, v }) => <div><dt className="text-sm text-ink-soft">{k}</dt><dd className="break-words font-semibold">{v}</dd></div>

function PasswordForm() {
  const toast = useToast()
  const empty = { current_password: '', new_password: '', confirm: '' }
  const [form, setForm] = useState(empty)
  const [errors, setErrors] = useState({})
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => { setForm({ ...form, [k]: e.target.value }); setErrors({ ...errors, [k]: undefined }) }

  async function submit(e) {
    e.preventDefault()
    const found = {}
    if (!form.current_password) found.current_password = 'Enter your current password'
    if (form.new_password.length < 8 || !/[A-Za-z]/.test(form.new_password) || !/\d/.test(form.new_password))
      found.new_password = 'Use at least 8 characters with a letter and a number'
    if (form.confirm !== form.new_password) found.confirm = 'Passwords do not match'
    setErrors(found)
    if (Object.keys(found).length) return
    setBusy(true)
    try {
      await api.changePassword({ current_password: form.current_password, new_password: form.new_password })
      toast.success('Password changed')
      setForm(empty)
    } catch (err) {
      if (err.status === 400) setErrors({ current_password: err.message })
      else toast.error(err.message)
    } finally { setBusy(false) }
  }

  return (
    <Panel title="Change password">
      <form onSubmit={submit} noValidate className="space-y-4">
        <TextField label="Current password" type="password" autoComplete="current-password" value={form.current_password} onChange={set('current_password')} error={errors.current_password} />
        <TextField label="New password" type="password" autoComplete="new-password" value={form.new_password} onChange={set('new_password')} error={errors.new_password} hint="At least 8 characters, with a letter and a number." />
        <TextField label="Confirm new password" type="password" autoComplete="new-password" value={form.confirm} onChange={set('confirm')} error={errors.confirm} />
        <Button type="submit" loading={busy}>Update password</Button>
      </form>
    </Panel>
  )
}
