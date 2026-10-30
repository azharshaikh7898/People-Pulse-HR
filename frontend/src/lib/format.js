export const LEAVE_TYPES = [
  { value: 'annual', label: 'Annual leave' },
  { value: 'sick', label: 'Sick leave' },
  { value: 'casual', label: 'Casual leave' },
  { value: 'unpaid', label: 'Unpaid leave' },
]
export const TASK_STATUSES = [
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In progress' },
  { value: 'completed', label: 'Completed' },
]
export const TASK_CATEGORIES = [
  { value: 'it_setup', label: 'IT setup' },
  { value: 'documentation', label: 'Documentation' },
  { value: 'hr_orientation', label: 'HR orientation' },
]
export const LEAVE_STATUSES = [
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'cancelled', label: 'Cancelled' },
]

const labelOf = (list) => (v) => list.find((x) => x.value === v)?.label ?? v
export const leaveTypeLabel = labelOf(LEAVE_TYPES)
export const categoryLabel = labelOf(TASK_CATEGORIES)

const dateFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
const shortFmt = new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'short' })

// API dates are plain 'YYYY-MM-DD'. Parse as local to avoid timezone off-by-one errors.
export function parseDate(iso) {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number)
  return new Date(y, m - 1, d)
}
export const formatDate = (iso) => (iso ? dateFmt.format(parseDate(iso)) : '-')
export function formatRange(start, end) {
  if (start === end) return formatDate(start)
  const sameYear = start.slice(0, 4) === end.slice(0, 4)
  return `${sameYear ? shortFmt.format(parseDate(start)) : formatDate(start)} to ${formatDate(end)}`
}
export function timeAgo(iso) {
  const mins = Math.round((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins} min ago`
  const hours = Math.round(mins / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  return days < 30 ? `${days} d ago` : formatDate(iso)
}
export const todayISO = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
export function workingDays(startISO, endISO) {
  if (!startISO || !endISO || endISO < startISO) return 0
  let n = 0
  for (let d = parseDate(startISO); d <= parseDate(endISO); d.setDate(d.getDate() + 1)) {
    if (d.getDay() !== 0 && d.getDay() !== 6) n++
  }
  return n
}
export const initials = (name = '') => name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()
