import { useEffect, useState } from 'react'

export interface DateRange { start: string; end: string }

function readRange(): DateRange {
  return { start: localStorage.getItem('fleetopt-date-start') || '', end: localStorage.getItem('fleetopt-date-end') || '' }
}

export function useDateRange() {
  const [range, setRange] = useState<DateRange>(readRange)
  useEffect(() => {
    const update = (event: Event) => setRange((event as CustomEvent<DateRange>).detail || readRange())
    window.addEventListener('fleetopt-date-range', update)
    return () => window.removeEventListener('fleetopt-date-range', update)
  }, [])
  return range
}
