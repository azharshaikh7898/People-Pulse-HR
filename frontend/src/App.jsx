import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout.jsx'
import { Spinner } from './components/ui.jsx'
import { useAuth } from './context/AuthContext.jsx'
import Dashboard from './pages/Dashboard.jsx'
import EmployeeDetails from './pages/EmployeeDetails.jsx'
import EmployeeForm from './pages/EmployeeForm.jsx'
import Employees from './pages/Employees.jsx'
import Leave from './pages/Leave.jsx'
import Login from './pages/Login.jsx'
import NotFound from './pages/NotFound.jsx'
import Onboarding from './pages/Onboarding.jsx'
import Profile from './pages/Profile.jsx'

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) return <Spinner label="Restoring your session" />
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />
  return children
}

// The backend enforces roles too; this just keeps employees from seeing pages that would only show errors.
function RequireHr({ children }) {
  const { isHr } = useAuth()
  return isHr ? children : <Navigate to="/" replace />
}

export default function App() {
  const { user, loading } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={loading ? <Spinner /> : user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<RequireAuth><Layout /></RequireAuth>}>
        <Route index element={<Dashboard />} />
        <Route path="employees" element={<RequireHr><Employees /></RequireHr>} />
        <Route path="employees/new" element={<RequireHr><EmployeeForm /></RequireHr>} />
        <Route path="employees/:id" element={<EmployeeDetails />} />
        <Route path="employees/:id/edit" element={<RequireHr><EmployeeForm /></RequireHr>} />
        <Route path="leave" element={<Leave />} />
        <Route path="onboarding" element={<Onboarding />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
