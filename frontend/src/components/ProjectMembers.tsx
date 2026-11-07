import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { UserPlus, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import type { ProjectMember, ProjectRole } from '../types'
import { useSession } from '../app/SessionProvider'
import { useToast } from '../app/ToastProvider'
import { ConfirmDialog } from './ConfirmDialog'
import { EmptyState, ErrorState, LoadingBlock, Pill } from './ui'
import { titleCase } from '../utils/format'

const ROLE_TONE: Record<ProjectRole, 'neutral' | 'blue' | 'green'> = {
  viewer: 'neutral',
  editor: 'blue',
  project_owner: 'green',
}

const ROLES: ProjectRole[] = ['viewer', 'editor', 'project_owner']

/**
 * Project membership administration.
 *
 * The controls are hidden for viewers, but that is only courtesy: the API
 * enforces ``assert_project_manage`` on every write, so hiding a button is never
 * the security boundary.
 */
export function ProjectMembers({ projectId, canManage }: { projectId: string; canManage: boolean }) {
  const { users } = useSession()
  const toast = useToast()
  const queryClient = useQueryClient()
  const [selectedUser, setSelectedUser] = useState('')
  const [selectedRole, setSelectedRole] = useState<ProjectRole>('viewer')
  const [pendingRemoval, setPendingRemoval] = useState<ProjectMember | null>(null)

  const members = useQuery({
    queryKey: ['project-members', projectId],
    queryFn: () => api.get<ProjectMember[]>(`/projects/${projectId}/members`),
    enabled: Boolean(projectId),
  })

  const memberIds = useMemo(() => new Set((members.data ?? []).map((member) => member.user.id)), [members.data])
  const candidates = useMemo(
    () => users.filter((user) => !memberIds.has(user.id)),
    [users, memberIds],
  )

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['project-members', projectId] })
    void queryClient.invalidateQueries({ queryKey: ['projects'] })
    void queryClient.invalidateQueries({ queryKey: ['projects', 'context'] })
  }

  const addMember = useMutation({
    mutationFn: () =>
      api.post<ProjectMember>(`/projects/${projectId}/members`, {
        user_id: selectedUser,
        role: selectedRole,
      }),
    onSuccess: (member) => {
      invalidate()
      setSelectedUser('')
      setSelectedRole('viewer')
      toast.push({ title: 'Access granted', message: `${member.user.label} is now a ${member.role.replace('_', ' ')}.`, variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not grant access', message: (error as Error).message, variant: 'error' }),
  })

  const changeRole = useMutation({
    mutationFn: ({ id, role }: { id: string; role: ProjectRole }) =>
      api.patch<ProjectMember>(`/projects/${projectId}/members/${id}`, { role }),
    onSuccess: () => {
      invalidate()
      toast.push({ title: 'Role updated', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not change the role', message: (error as Error).message, variant: 'error' }),
  })

  const removeMember = useMutation({
    mutationFn: (id: string) => api.delete(`/projects/${projectId}/members/${id}`),
    onSuccess: () => {
      invalidate()
      setPendingRemoval(null)
      toast.push({ title: 'Access removed', message: 'The next request from that account is checked against the new membership.', variant: 'success' })
    },
    onError: (error) => {
      setPendingRemoval(null)
      toast.push({ title: 'Could not remove access', message: (error as Error).message, variant: 'error' })
    },
  })

  if (members.isLoading) return <LoadingBlock rows={4} label="Loading project members" />
  if (members.error) return <ErrorState message={(members.error as Error).message} onRetry={() => members.refetch()} />
  if (!members.data) return null

  return (
    <div className="stack stack-3">
      {members.data.length === 0 ? (
        <EmptyState
          title="No members recorded"
          description="Workspace administrators still have implicit access. Grant membership before relying on this project being visible to anyone else."
        />
      ) : (
        <div className="table-wrap">
          <table className="clh-table">
            <thead>
              <tr>
                <th>Member</th>
                <th>Email</th>
                <th>Role in this project</th>
                {canManage && <th aria-label="Actions" />}
              </tr>
            </thead>
            <tbody>
              {members.data.map((member) => (
                <tr key={member.id}>
                  <td>
                    <div style={{ fontWeight: 560 }}>{member.user.label}</div>
                    {member.user.sublabel && <div className="cell-sub">{member.user.sublabel}</div>}
                  </td>
                  <td className="text-secondary-clh">{member.email || '—'}</td>
                  <td>
                    {canManage ? (
                      <select
                        className="form-select form-select-sm"
                        style={{ maxWidth: 190 }}
                        aria-label={`Role for ${member.user.label}`}
                        value={member.role}
                        onChange={(event) =>
                          changeRole.mutate({ id: member.id, role: event.target.value as ProjectRole })
                        }
                        disabled={changeRole.isPending}
                      >
                        {ROLES.map((role) => (
                          <option key={role} value={role}>
                            {titleCase(role)}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Pill tone={ROLE_TONE[member.role]}>{titleCase(member.role)}</Pill>
                    )}
                  </td>
                  {canManage && (
                    <td style={{ textAlign: 'right' }}>
                      <button
                        type="button"
                        className="btn btn-ghost btn-sm"
                        aria-label={`Remove access for ${member.user.label}`}
                        onClick={() => setPendingRemoval(member)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {canManage && (
        <div className="card-surface" style={{ padding: 12, boxShadow: 'none' }}>
          <div className="meta-label mb-2">Grant access</div>
          {candidates.length === 0 ? (
            <div className="definition">Every active team member already has access to this project.</div>
          ) : (
            <div className="d-flex flex-wrap gap-2 align-items-end">
              <div style={{ minWidth: 220, flex: 1 }}>
                <label className="form-label" htmlFor="member-user">
                  Team member
                </label>
                <select
                  id="member-user"
                  className="form-select form-select-sm"
                  value={selectedUser}
                  onChange={(event) => setSelectedUser(event.target.value)}
                >
                  <option value="">Select a person</option>
                  {candidates.map((user) => (
                    <option key={user.id} value={user.id}>
                      {user.name} · {titleCase(user.role)}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ minWidth: 150 }}>
                <label className="form-label" htmlFor="member-role">
                  Role
                </label>
                <select
                  id="member-role"
                  className="form-select form-select-sm"
                  value={selectedRole}
                  onChange={(event) => setSelectedRole(event.target.value as ProjectRole)}
                >
                  {ROLES.map((role) => (
                    <option key={role} value={role}>
                      {titleCase(role)}
                    </option>
                  ))}
                </select>
              </div>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                disabled={!selectedUser || addMember.isPending}
                onClick={() => addMember.mutate()}
              >
                <UserPlus size={13} /> {addMember.isPending ? 'Granting…' : 'Grant access'}
              </button>
            </div>
          )}
          <div className="definition mt-2">
            A viewer can read the project. An editor can change its research records. A project owner can also manage
            this member list. Workspace administrators always have access.
          </div>
        </div>
      )}

      <ConfirmDialog
        show={Boolean(pendingRemoval)}
        title="Remove project access?"
        destructive
        confirmLabel="Remove access"
        busy={removeMember.isPending}
        onCancel={() => setPendingRemoval(null)}
        onConfirm={() => pendingRemoval && removeMember.mutate(pendingRemoval.id)}
      >
        <p style={{ marginBottom: 8 }}>
          {pendingRemoval?.user.label} will lose access to this project immediately. Their historical records stay
          intact and the change is written to the project activity log.
        </p>
      </ConfirmDialog>
    </div>
  )
}
