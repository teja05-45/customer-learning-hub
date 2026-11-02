import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Database, Download, ShieldAlert, Trash2, Users } from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../app/ToastProvider'
import { useSession } from '../app/SessionProvider'
import type { Health, OrgSettings } from '../types'
import {
  ErrorState,
  LoadingBlock,
  Notice,
  PageHeader,
  Pill,
  SectionCard,
} from '../components/ui'
import { ConfirmDialog } from '../components/ConfirmDialog'
import { titleCase } from '../utils/format'

const EXPORTS = [
  { entity: 'projects', label: 'Research projects' },
  { entity: 'participants', label: 'Participants' },
  { entity: 'recruitment', label: 'Recruitment records' },
  { entity: 'interviews', label: 'Interviews' },
  { entity: 'evidence', label: 'Evidence' },
  { entity: 'insights', label: 'Insights' },
  { entity: 'decisions', label: 'Decisions' },
  { entity: 'actions', label: 'Actions' },
]

export function SettingsPage() {
  const toast = useToast()
  const queryClient = useQueryClient()
  const { user, users } = useSession()
  const [resetOpen, setResetOpen] = useState(false)
  const [form, setForm] = useState({ name: '', retention_months: 12, show_demo_banner: true })

  const settings = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.get<OrgSettings>('/settings'),
  })

  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api.get<Health>('/health'),
    refetchInterval: 30_000,
  })

  useEffect(() => {
    if (settings.data) {
      setForm({
        name: settings.data.name,
        retention_months: settings.data.retention_months,
        show_demo_banner: settings.data.show_demo_banner,
      })
    }
  }, [settings.data])

  const saveSettings = useMutation({
    mutationFn: () => api.patch<OrgSettings>('/settings', form),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['settings'] })
      toast.push({ title: 'Settings saved', variant: 'success' })
    },
    onError: (error) => toast.push({ title: 'Could not save settings', message: (error as Error).message, variant: 'error' }),
  })

  const resetDemo = useMutation({
    mutationFn: () => api.post('/demo/reset', { confirm: true, phrase: 'RESET' }),
    onSuccess: () => {
      setResetOpen(false)
      void queryClient.invalidateQueries()
      toast.push({
        title: 'Demo data restored',
        message: 'Every screen now shows the original synthetic dataset.',
        variant: 'success',
      })
    },
    onError: (error) => toast.push({ title: 'Reset failed', message: (error as Error).message, variant: 'error' }),
  })

  const download = async (entity: string, label: string) => {
    try {
      await api.downloadCsv(`/exports/${entity}.csv`, `everyday-goods-${entity}-synthetic.csv`)
      toast.push({ title: `${label} exported`, message: 'The CSV is labelled as synthetic data.', variant: 'success' })
    } catch (error) {
      toast.push({ title: 'Export failed', message: (error as Error).message, variant: 'error' })
    }
  }

  return (
    <div className="page" style={{ maxWidth: 1180 }}>
      <PageHeader
        title="Settings"
        description="Organisation configuration, access model, data handling and the exports the team can take away."
        meta={
          <div className="inline" style={{ gap: 8 }}>
            <Pill tone={health.data?.status === 'ok' ? 'green' : 'red'}>
              API {health.data?.status ?? 'unknown'}
            </Pill>
            <Pill tone="outline">v{health.data?.version ?? '—'}</Pill>
            <Pill tone="amber">{health.data?.demo_mode ? 'Demo mode' : 'Live mode'}</Pill>
            <span className="definition">
              Database {health.data?.database ?? '—'} · seeded {String(health.data?.seeded ?? false)}
            </span>
          </div>
        }
      />

      <div className="section-grid grid-sidebar">
        <div className="stack stack-3">
          <SectionCard title="Organisation" subtitle="Applies to everyone using this workspace">
            {settings.isLoading && <LoadingBlock rows={4} />}
            {settings.error && <ErrorState message="Settings could not be loaded." onRetry={() => settings.refetch()} />}
            {settings.data && (
              <div className="stack stack-3">
                <div className="section-grid grid-2" style={{ gap: 12 }}>
                  <div>
                    <label className="form-label" htmlFor="org-name">
                      Organisation name
                    </label>
                    <input
                      id="org-name"
                      className="form-control"
                      value={form.name}
                      onChange={(event) => setForm({ ...form, name: event.target.value })}
                    />
                  </div>
                  <div>
                    <label className="form-label" htmlFor="retention-months">
                      Retention period (months)
                    </label>
                    <input
                      id="retention-months"
                      type="number"
                      min={1}
                      max={120}
                      className="form-control"
                      value={form.retention_months}
                      onChange={(event) => setForm({ ...form, retention_months: Number(event.target.value) })}
                    />
                    <div className="form-text">
                      Assumption recorded for handover. Automatic deletion is not implemented in this prototype.
                    </div>
                  </div>
                </div>
                <label className="inline" style={{ gap: 8, fontSize: 13 }}>
                  <input
                    type="checkbox"
                    checked={form.show_demo_banner}
                    onChange={(event) => setForm({ ...form, show_demo_banner: event.target.checked })}
                  />
                  Show the synthetic-data banner across the workspace
                </label>
                <div>
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => saveSettings.mutate()}
                    disabled={saveSettings.isPending}
                  >
                    {saveSettings.isPending ? 'Saving…' : 'Save organisation settings'}
                  </button>
                </div>
              </div>
            )}
          </SectionCard>

          <SectionCard
            title="Users and roles"
            subtitle="Demonstration identities. No passwords, sessions or tokens exist behind them."
            icon={<Users size={14} />}
          >
            <div className="table-wrap">
              <table className="clh-table">
                <thead>
                  <tr>
                    <th>Person</th>
                    <th>Role</th>
                    <th>What the role is for</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {users.map((entry) => (
                    <tr key={entry.id}>
                      <td>
                        <span style={{ fontWeight: 600 }}>{entry.name}</span>
                        <div className="cell-sub">{entry.job_title}</div>
                      </td>
                      <td>
                        <Pill tone="outline">{titleCase(entry.role)}</Pill>
                      </td>
                      <td className="text-secondary-clh">{entry.description}</td>
                      <td>{entry.id === user?.id ? <Pill tone="green">Current</Pill> : null}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-3">
              <Notice tone="warning" icon={<ShieldAlert size={15} />} title="Not a security boundary">
                Role switching changes the demonstration entry point only. Every API request in this prototype is served
                with the same permissions. Real authentication, sessions and server-side authorisation are a documented
                dependency, not an implemented feature.
              </Notice>
            </div>
          </SectionCard>

          <SectionCard
            title="Synthetic data exports"
            subtitle="CSV extracts of the demonstration dataset — every file is marked as synthetic"
            icon={<Download size={14} />}
          >
            <div className="section-grid grid-3" style={{ gap: 8 }}>
              {EXPORTS.map((entry) => (
                <button
                  key={entry.entity}
                  type="button"
                  className="btn btn-outline-secondary btn-sm"
                  onClick={() => void download(entry.entity, entry.label)}
                >
                  <Download size={12} /> {entry.label}
                </button>
              ))}
            </div>
            <div className="definition mt-3">
              Exports include an <span className="mono">is_synthetic</span> column and an export timestamp, so a
              spreadsheet taken out of context cannot be mistaken for real customer data.
            </div>
          </SectionCard>
        </div>

        <div className="stack stack-3">
          <SectionCard title="Data handling" subtitle="What this prototype does and deliberately does not do" icon={<Database size={14} />}>
            <ul className="definition" style={{ paddingLeft: 16, lineHeight: 1.7, margin: 0 }}>
              <li>All people, conversations and outcomes are synthetic and generated locally.</li>
              <li>No contact details are stored, so none can be exported or searched.</li>
              <li>No connection exists to Everyday Goods commerce, support or CRM systems.</li>
              <li>No customer is contacted, by any channel.</li>
              <li>No audio is recorded and recording is off by default.</li>
              <li>Evidence without recorded provenance is flagged and cannot be presented as verified.</li>
              <li>Deleting evidence removes its insight links, which is visible in the insight's evidence count.</li>
            </ul>
          </SectionCard>

          <SectionCard title="Danger zone" subtitle="Restore the demonstration starting point">
            <Notice tone="danger" title="This discards your changes">
              Any project, participant, interview, evidence, insight, decision or action you created during the demo will
              be replaced by the original synthetic dataset. Type RESET to confirm.
            </Notice>
            <div className="mt-3">
              <button type="button" className="btn btn-danger-soft" onClick={() => setResetOpen(true)}>
                <Trash2 size={13} /> Reset demo data
              </button>
            </div>
          </SectionCard>

          <SectionCard title="Environment">
            <div className="stack stack-2">
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span className="definition">API environment</span>
                <span className="mono">{health.data?.environment ?? '—'}</span>
              </div>
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span className="definition">Last health check</span>
                <span className="mono">
                  {health.data ? new Date(health.data.checked_at).toLocaleTimeString() : '—'}
                </span>
              </div>
              <div className="row-between" style={{ fontSize: 12.5 }}>
                <span className="definition">Demo data present</span>
                <span className="mono">{String(health.data?.seeded ?? false)}</span>
              </div>
            </div>
          </SectionCard>
        </div>
      </div>

      <ConfirmDialog
        show={resetOpen}
        title="Reset all demo data?"
        destructive
        confirmLabel="Reset demo data"
        requirePhrase="RESET"
        busy={resetDemo.isPending}
        onCancel={() => setResetOpen(false)}
        onConfirm={() => resetDemo.mutate()}
      >
        <p style={{ marginBottom: 8 }}>
          The workspace returns to the original synthetic dataset. Anything you created during the demonstration is
          permanently discarded.
        </p>
        <div className="definition">
          The API refuses this request unless the confirmation phrase matches, so it cannot happen by accident.
        </div>
      </ConfirmDialog>
    </div>
  )
}

