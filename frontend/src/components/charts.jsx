// Small hand-built charts. Every chart also shows its numbers as text, so it never relies on colour alone.
export const SERIES = {
  completed: '#1f6b46', in_progress: '#24589c', pending: '#e29a2b',
  approved: '#1f6b46', rejected: '#a5301f',
}

export function BarList({ items, color = '#0e6b66', unit = '' }) {
  const max = Math.max(1, ...items.map((i) => i.value))
  return (
    <ul className="space-y-3">
      {items.map((i) => (
        <li key={i.label}>
          <div className="mb-1 flex justify-between text-sm">
            <span className="font-medium">{i.label}</span>
            <span className="tabular-nums text-ink-soft">{i.value}{unit}</span>
          </div>
          <div className="h-2.5 rounded-full bg-canvas" role="img" aria-label={`${i.label}: ${i.value}`}>
            <div className="h-full rounded-full" style={{ width: `${(i.value / max) * 100}%`, background: color }} />
          </div>
        </li>
      ))}
    </ul>
  )
}

export function StackedBar({ segments, label }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  return (
    <div>
      <div className="flex h-5 w-full overflow-hidden rounded-md bg-canvas" role="img"
           aria-label={`${label}: ${segments.map((s) => `${s.value} ${s.label}`).join(', ')}`}>
        {total > 0 && segments.map((s) => (
          <div key={s.label} style={{ width: `${(s.value / total) * 100}%`, background: s.color }} className="border-r-2 border-panel last:border-r-0" />
        ))}
      </div>
      <dl className="mt-3 flex flex-wrap gap-x-6 gap-y-2">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} aria-hidden="true" />
            <dt className="text-ink-soft">{s.label}</dt>
            <dd className="font-bold tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

export function Donut({ segments, centerLabel }) {
  const total = segments.reduce((s, x) => s + x.value, 0)
  const R = 52, C = 2 * Math.PI * R
  let offset = 0
  return (
    <div className="flex flex-wrap items-center gap-6">
      <svg viewBox="0 0 140 140" className="h-36 w-36 shrink-0" role="img"
           aria-label={`${centerLabel}: ${segments.map((s) => `${s.value} ${s.label}`).join(', ')}`}>
        <circle cx="70" cy="70" r={R} fill="none" stroke="#eef1ea" strokeWidth="18" />
        {total > 0 && segments.map((s) => {
          const len = (s.value / total) * C
          const el = <circle key={s.label} cx="70" cy="70" r={R} fill="none" stroke={s.color} strokeWidth="18"
                             strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-offset} transform="rotate(-90 70 70)" />
          offset += len
          return el
        })}
        <text x="70" y="68" textAnchor="middle" className="fill-ink" style={{ font: '700 26px var(--font-display)' }}>{total}</text>
        <text x="70" y="86" textAnchor="middle" className="fill-ink-soft" style={{ font: '500 10px var(--font-sans)' }}>{centerLabel}</text>
      </svg>
      <dl className="space-y-2">
        {segments.map((s) => (
          <div key={s.label} className="flex items-center gap-2 text-sm">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: s.color }} aria-hidden="true" />
            <dt className="w-20 text-ink-soft">{s.label}</dt>
            <dd className="font-bold tabular-nums">{s.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
