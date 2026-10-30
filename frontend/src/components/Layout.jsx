import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { CalendarDays, ClipboardCheck, LayoutDashboard, LogOut, Menu, UserCircle, Users, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import { Avatar, cx } from './ui.jsx'

export function Logo({ light = true }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill={light ? '#0b2d2b' : '#0f3b38'} />
        <path d="M4 17h6l3-8 5 15 3-7h7" fill="none" stroke="#f0b04a" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span className={cx('font-display text-xl font-bold tracking-tight', light ? 'text-white' : 'text-brand-900')}>PeoplePulse</span>
    </span>
  )
}

function useNav(isHr) {
  return [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
    ...(isHr ? [{ to: '/employees', label: 'Employees', icon: Users }] : []),
    { to: '/leave', label: 'Leave', icon: CalendarDays },
    { to: '/onboarding', label: 'Onboarding', icon: ClipboardCheck },
    { to: '/profile', label: 'Profile', icon: UserCircle },
  ]
}

function SidebarContent({ onNavigate }) {
  const { user, isHr, logout } = useAuth()
  const nav = useNav(isHr)
  return (
    <div className="flex h-full flex-col bg-brand-900 text-white">
      <div className="px-5 pb-6 pt-6"><Logo /></div>
      <nav aria-label="Main" className="flex-1 space-y-1 px-3">
        {nav.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} onClick={onNavigate}
            className={({ isActive }) => cx(
              'relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-semibold transition-colors',
              isActive ? 'bg-white/10 text-white' : 'text-white/70 hover:bg-white/5 hover:text-white',
            )}>
            {({ isActive }) => (
              <>
                {isActive && <span className="absolute inset-y-2 left-0 w-1 rounded-r bg-saffron-500" aria-hidden="true" />}
                <Icon size={18} aria-hidden="true" />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-white/10 p-4">
        <div className="mb-3 flex items-center gap-3">
          <Avatar name={user.display_name} />
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{user.display_name}</p>
            <p className="truncate text-xs text-white/60">{isHr ? 'HR administrator' : 'Employee'}</p>
          </div>
        </div>
        <button type="button" onClick={logout}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-white/80 hover:bg-white/10 hover:text-white">
          <LogOut size={16} aria-hidden="true" /> Sign out
        </button>
      </div>
    </div>
  )
}

export default function Layout() {
  const [open, setOpen] = useState(false)
  const { pathname } = useLocation()

  useEffect(() => { setOpen(false) }, [pathname])
  useEffect(() => {
    if (!open) return
    const onKey = (e) => e.key === 'Escape' && setOpen(false)
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  return (
    <div className="min-h-full lg:grid lg:grid-cols-[250px_1fr]">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-[70] focus:rounded-lg focus:bg-white focus:px-4 focus:py-2 focus:font-semibold focus:shadow-lg">
        Skip to main content
      </a>

      <aside className="sticky top-0 hidden h-screen lg:block"><SidebarContent /></aside>

      <header className="sticky top-0 z-30 flex items-center justify-between bg-brand-900 px-4 py-3 lg:hidden">
        <Logo />
        <button type="button" onClick={() => setOpen(true)} aria-label="Open menu" aria-expanded={open}
                className="rounded-lg p-2 text-white hover:bg-white/10"><Menu size={22} /></button>
      </header>

      {open && (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-brand-950/60" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85%] shadow-2xl">
            <button type="button" onClick={() => setOpen(false)} aria-label="Close menu"
                    className="absolute right-2 top-3 z-10 rounded-lg p-2 text-white hover:bg-white/10"><X size={20} /></button>
            <SidebarContent onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}

      <main id="main" tabIndex={-1} className="min-w-0 px-4 py-6 sm:px-8 sm:py-8">
        <div className="mx-auto max-w-6xl"><Outlet /></div>
      </main>
    </div>
  )
}
