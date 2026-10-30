import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Logo } from '../components/Layout.jsx'
import { Button, TextField } from '../components/ui.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { useToast } from '../context/ToastContext.jsx'

// Shown only by `npm run dev`. They are removed from production builds.
const DEV_ACCOUNTS = import.meta.env.DEV ? [
  { label: 'HR administrator', email: 'hr.admin@example.com', password: 'HrAdmin#2026' },
  { label: 'Employee', email: 'demo.employee@example.com', password: 'Employee#2026' },
] : []

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const toast = useToast()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e) {
    e.preventDefault()
    setError('')
    setBusy(true)
    try {
      const user = await login(form.email.trim(), form.password)
      toast.success(`Welcome back, ${user.display_name.split(' ')[0]}`)
      navigate(location.state?.from?.pathname || '/', { replace: true })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="grid min-h-full lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden overflow-hidden bg-brand-900 p-12 text-white lg:flex lg:flex-col lg:justify-between">
        <Logo />
        <div className="relative z-10 max-w-md">
          <h1 className="font-display text-4xl font-bold leading-tight">New hires productive by their first Friday.</h1>
          <p className="mt-4 text-lg text-white/70">Employee records, leave approvals and onboarding checklists, tracked in one place.</p>
        </div>
        <svg viewBox="0 0 600 120" className="absolute inset-x-0 bottom-24 w-full opacity-30" aria-hidden="true" preserveAspectRatio="none">
          <path d="M0 70h170l28-48 44 96 36-60 24 12h98l30-42 42 84 26-42H600" fill="none" stroke="#f0b04a" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <p className="relative z-10 text-sm text-white/50">PeoplePulse · People tech and analytics</p>
      </section>

      <main className="flex items-center justify-center px-5 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 lg:hidden"><Logo light={false} /></div>
          <h2 className="text-2xl font-bold">Sign in</h2>
          <p className="mt-1 text-ink-soft">Use the email and password HR gave you.</p>

          <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
            {error && <div role="alert" className="rounded-lg border border-bad-700/30 bg-bad-50 px-4 py-3 text-sm font-medium text-bad-700">{error}</div>}
            <TextField label="Email" type="email" autoComplete="username" required value={form.email}
                       onChange={(e) => setForm({ ...form, email: e.target.value })} />
            <TextField label="Password" type="password" autoComplete="current-password" required value={form.password}
                       onChange={(e) => setForm({ ...form, password: e.target.value })} />
            <Button type="submit" loading={busy} className="w-full" disabled={!form.email || !form.password}>Sign in</Button>
          </form>

          {DEV_ACCOUNTS.length > 0 && (
            <div className="mt-8 rounded-lg border border-dashed border-line-strong p-4">
              <p className="text-xs font-semibold text-ink-soft">Development only: fill in a demo account</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {DEV_ACCOUNTS.map((a) => (
                  <Button key={a.email} variant="secondary" size="sm" onClick={() => setForm({ email: a.email, password: a.password })}>{a.label}</Button>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
