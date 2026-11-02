import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, getDemoUserId, setDemoUserId } from '../services/api'
import type { DemoUser, Session } from '../types'

interface SessionContextValue {
  session: Session | undefined
  isLoading: boolean
  error: unknown
  user: DemoUser | null
  users: DemoUser[]
  enter: (user: DemoUser) => void
  leave: () => void
  refetchSession: () => void
  isDemo: boolean
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function SessionProvider({ children }: { children: ReactNode }) {
  const [selectedId, setSelectedId] = useState<string | null>(() => getDemoUserId())

  const query = useQuery({
    queryKey: ['session'],
    queryFn: () => api.get<Session>('/session'),
    staleTime: 60_000,
  })

  const users = query.data?.users ?? []
  const user = useMemo(() => users.find((entry) => entry.id === selectedId) ?? null, [users, selectedId])

  const enter = useCallback((nextUser: DemoUser) => {
    // A demonstration entry: the id is kept locally so a refresh does not lose
    // context. It is not a credential and grants nothing on its own.
    setDemoUserId(nextUser.id)
    setSelectedId(nextUser.id)
  }, [])

  const leave = useCallback(() => {
    setDemoUserId(null)
    setSelectedId(null)
  }, [])

  const value: SessionContextValue = {
    session: query.data,
    isLoading: query.isLoading,
    error: query.error,
    user,
    users,
    enter,
    leave,
    refetchSession: () => {
      void query.refetch()
    },
    isDemo: query.data?.demo_mode ?? true,
  }

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
}

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext)
  if (!context) throw new Error('useSession must be used inside SessionProvider')
  return context
}
