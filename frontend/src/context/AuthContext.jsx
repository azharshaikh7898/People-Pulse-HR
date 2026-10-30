import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, tokenStore } from '../services/api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(Boolean(tokenStore.get()))

  // Restore the session on page load.
  useEffect(() => {
    if (!tokenStore.get()) return
    api.me().then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false))
  }, [])

  // The API client fires this when the server says the token is no longer valid.
  useEffect(() => {
    const onUnauthorized = () => setUser(null)
    window.addEventListener('peoplepulse:unauthorized', onUnauthorized)
    return () => window.removeEventListener('peoplepulse:unauthorized', onUnauthorized)
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await api.login(email, password)
    tokenStore.set(res.access_token)
    setUser(res.user)
    return res.user
  }, [])

  const logout = useCallback(async () => {
    try { await api.logout() } catch { /* token may already be invalid; sign out locally anyway */ }
    tokenStore.clear()
    setUser(null)
  }, [])

  const value = useMemo(() => ({ user, loading, login, logout, isHr: user?.role === 'hr_admin' }), [user, loading, login, logout])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
