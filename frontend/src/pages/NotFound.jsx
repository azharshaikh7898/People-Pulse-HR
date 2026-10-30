import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { EmptyState } from '../components/ui.jsx'

export default function NotFound() {
  return (
    <EmptyState icon={Compass} title="Page not found" message="The page you are looking for does not exist or was moved."
      action={<Link to="/" className="font-semibold text-brand-600 underline">Back to the dashboard</Link>} />
  )
}
