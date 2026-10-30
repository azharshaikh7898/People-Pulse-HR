import { useCallback, useEffect, useRef, useState } from 'react'

// Runs an async function whenever `deps` change. Ignores results from outdated calls.
export function useAsync(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const latest = useRef(0)

  const run = useCallback(() => {
    const id = ++latest.current
    setState((s) => ({ ...s, loading: true, error: null }))
    fn().then(
      (data) => id === latest.current && setState({ data, error: null, loading: false }),
      (error) => id === latest.current && setState({ data: null, error, loading: false }),
    )
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => { run() }, [run])
  return { ...state, reload: run }
}

export function useDebounced(value, delay = 300) {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return v
}
