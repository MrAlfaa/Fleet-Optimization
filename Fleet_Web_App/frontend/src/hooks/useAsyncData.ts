import { useCallback, useEffect, useRef, useState } from 'react'
import type { DependencyList, Dispatch, SetStateAction } from 'react'

export interface AsyncState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => Promise<void>
  setData: Dispatch<SetStateAction<T | null>>
}

export function useAsyncData<T>(loader: () => Promise<T>, dependencies: DependencyList = []): AsyncState<T> {
  const loaderRef = useRef(loader)
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loaderRef.current = loader
  }, [loader])

  const reload = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await loaderRef.current())
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    queueMicrotask(() => {
      void reload()
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload, ...dependencies])

  return { data, error, loading, reload, setData }
}
