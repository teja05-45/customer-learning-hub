import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../services/api'
import type { ProjectListResponse, ProjectRole, ProjectSummary } from '../types'

/**
 * The active research project.
 *
 * The selection is a convenience for the human, never a permission: every
 * request still carries its own project id and the API re-checks membership.
 * Keeping the choice in localStorage makes a refresh land on the same study.
 */

const STORAGE_KEY = 'clh.activeProjectId'

interface ProjectContextValue {
  projects: ProjectSummary[]
  activeProject: ProjectSummary | null
  activeProjectId: string | null
  role: ProjectRole | null
  canWrite: boolean
  canManage: boolean
  isLoading: boolean
  selectProject: (projectId: string | null) => void
  refetch: () => void
}

const ProjectContext = createContext<ProjectContextValue | null>(null)

const RANK: Record<ProjectRole, number> = { viewer: 1, editor: 2, project_owner: 3 }

export function ProjectProvider({ children }: { children: ReactNode }) {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(() =>
    typeof window === 'undefined' ? null : window.localStorage.getItem(STORAGE_KEY),
  )

  const query = useQuery({
    queryKey: ['projects', 'context'],
    queryFn: () => api.get<ProjectListResponse>('/projects?page_size=100'),
    staleTime: 30_000,
  })

  const projects = useMemo(() => query.data?.items ?? [], [query.data])

  // A project the user has lost access to (or one that was deleted) must not
  // stay selected and quietly show an empty workspace.
  useEffect(() => {
    if (!query.isFetched) return
    if (activeProjectId && !projects.some((project) => project.id === activeProjectId)) {
      setActiveProjectId(null)
      window.localStorage.removeItem(STORAGE_KEY)
    }
  }, [activeProjectId, projects, query.isFetched])

  const selectProject = useCallback((projectId: string | null) => {
    setActiveProjectId(projectId)
    if (projectId) window.localStorage.setItem(STORAGE_KEY, projectId)
    else window.localStorage.removeItem(STORAGE_KEY)
  }, [])

  const activeProject = projects.find((project) => project.id === activeProjectId) ?? null
  const role = activeProject?.role ?? null

  const value = useMemo<ProjectContextValue>(
    () => ({
      projects,
      activeProject,
      activeProjectId,
      role,
      canWrite: role ? RANK[role] >= RANK.editor : false,
      canManage: role ? RANK[role] >= RANK.project_owner : false,
      isLoading: query.isLoading,
      selectProject,
      refetch: () => void query.refetch(),
    }),
    [projects, activeProject, activeProjectId, role, query, selectProject],
  )

  return <ProjectContext.Provider value={value}>{children}</ProjectContext.Provider>
}

export function useProject(): ProjectContextValue {
  const context = useContext(ProjectContext)
  if (!context) throw new Error('useProject must be used inside ProjectProvider')
  return context
}
