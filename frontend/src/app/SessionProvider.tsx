import { createContext, useCallback, useContext, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ApiError, api } from '../services/api'
import type { DemoUser, Session } from '../types'

interface SessionContextValue {
  session: Session | undefined
  isLoading: boolean
  error: unknown
  user: DemoUser | null
  users: DemoUser[]
  enter: (user: DemoUser) => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  leave: () => Promise<void>
  refetchSession: () => void
  isDemo: boolean
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  // The directory is public and only drives the entry screen.
  const directory = useQuery({
    queryKey: ['session'],
    queryFn: () => api.get<Session>('/session'),
    staleTime: 60_000,
  })

  // Identity comes from the server session cookie, never from local storage.
  const me = useQuery({
    queryKey: ['auth-me'],
    queryFn: () => api.get<DemoUser>('/auth/me'),
    retry: false,
    staleTime: 15_000,
  })

  const refresh = useCallback(async () => {
    await Promise.all([me.refetch(), directory.refetch()])
  }, [me, directory])

  const enter = useCallback(
    async (nextUser: DemoUser) => {
      await api.post('/auth/demo', { user_id: nextUser.id })
      await refresh()
    },
    [refresh],
  )

  const signIn = useCallback(
    async (email: string, password: string) => {
      await api.post('/auth/login', { email, password })
      await refresh()
    },
    [refresh],
  )

  const leave = useCallback(async () => {
    await api.post('/auth/logout')
    await refresh()
  }, [refresh])

  const notSignedIn = me.error instanceof ApiError && me.error.status === 401
  const error = directory.error ?? (me.error && !notSignedIn ? me.error : null)

  return (
    <SessionContext.Provider
      value={{
        session: directory.data,
        isLoading: directory.isLoading || me.isLoading,
        error,
        user: me.data ?? null,
        users: directory.data?.users ?? [],
        enter,
        signIn,
        leave,
        refetchSession: () => {
          void refresh()
        },
        isDemo: directory.data?.demo_mode ?? true,
      }}
    >
      {children}
    </SessionContext.Provider>
  )
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be used inside SessionProvider')
  return context
}
