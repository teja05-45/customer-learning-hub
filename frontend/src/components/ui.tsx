import type { ReactNode } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Info,
  Inbox,
  Loader2,
  RefreshCw,
  ShieldAlert,
} from 'lucide-react'
import type { Tone } from '../utils/format'

/* ------------------------------------------------------------------ pills */
export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`pill pill-${tone}`}>{children}</span>
}

/* ------------------------------------------------------------- containers */
export function SectionCard({
  title,
  subtitle,
  actions,
  children,
  padded = true,
  icon,
}: {
  title?: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
  children: ReactNode
  padded?: boolean
  icon?: ReactNode
}) {
  return (
    <section className="card-surface" aria-label={typeof title === 'string' ? title : undefined}>
      {(title || actions) && (
        <div className="card-header-row">
          <div>
            <div className="card-title">
              {icon}
              {title}
            </div>
            {subtitle && <div className="card-subtitle">{subtitle}</div>}
          </div>
          {actions && <div className="page-actions">{actions}</div>}
        </div>
      )}
      <div className={padded ? 'card-section' : undefined}>{children}</div>
    </section>
  )
}

export function PageHeader({
  title,
  description,
  actions,
  meta,
}: {
  title: ReactNode
  description?: ReactNode
  actions?: ReactNode
  meta?: ReactNode
}) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        {description && <p className="page-description">{description}</p>}
        {meta && <div className="mt-2">{meta}</div>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  )
}

export function StatCard({
  label,
  value,
  meta,
  icon,
  warning = false,
  hint,
}: {
  label: ReactNode
  value: ReactNode
  meta?: ReactNode
  icon?: ReactNode
  warning?: boolean
  hint?: string
}) {
  return (
    <div className={`stat-card${warning ? ' is-warning' : ''}`} title={hint}>
      <div className="stat-label">
        {icon}
        {label}
      </div>
      <div className="stat-value">{value}</div>
      {meta && <div className="stat-meta">{meta}</div>}
    </div>
  )
}

/* ----------------------------------------------------------- empty/error */
export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string
  description?: ReactNode
  action?: ReactNode
  icon?: ReactNode
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon ?? <Inbox size={18} />}</div>
      <div className="empty-title">{title}</div>
      {description && <div className="empty-description">{description}</div>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = 'This view could not be loaded',
  message,
  onRetry,
}: {
  title?: string
  message: string
  onRetry?: () => void
}) {
  return (
    <div className="card-surface">
      <div className="empty-state">
        <div className="empty-icon" style={{ background: 'var(--clh-danger-soft)', color: 'var(--clh-danger)' }}>
          <ShieldAlert size={18} />
        </div>
        <div className="empty-title">{title}</div>
        <div className="empty-description">{message}</div>
        {onRetry && (
          <button type="button" className="btn btn-outline-secondary btn-sm mt-2" onClick={onRetry}>
            <RefreshCw size={13} /> Retry
          </button>
        )}
      </div>
    </div>
  )
}

export function LoadingBlock({ rows = 4, label }: { rows?: number; label?: string }) {
  return (
    <div aria-busy="true" aria-live="polite" className="stack stack-2" style={{ padding: 4 }}>
      {label && <div className="definition">{label}</div>}
      {Array.from({ length: rows }).map((_, index) => (
        <div className="skeleton" key={index} style={{ width: `${100 - index * 6}%`, height: 14 }} />
      ))}
    </div>
  )
}

export function TableSkeleton({ rows = 5, columns = 5 }: { rows?: number; columns?: number }) {
  return (
    <div className="table-wrap">
      <table className="clh-table">
        <thead>
          <tr>
            {Array.from({ length: columns }).map((_, index) => (
              <th key={index}>
                <div className="skeleton" style={{ width: 70 }} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex}>
              {Array.from({ length: columns }).map((_, columnIndex) => (
                <td key={columnIndex}>
                  <div className="skeleton" style={{ width: columnIndex === 0 ? '75%' : '50%' }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* --------------------------------------------------------------- notices */
export function Notice({
  tone = 'info',
  title,
  children,
  icon,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success' | 'neutral'
  title?: ReactNode
  children?: ReactNode
  icon?: ReactNode
}) {
  const fallback =
    tone === 'warning' ? (
      <AlertTriangle size={15} />
    ) : tone === 'danger' ? (
      <ShieldAlert size={15} />
    ) : tone === 'success' ? (
      <CheckCircle2 size={15} />
    ) : (
      <Info size={15} />
    )
  return (
    <div className={`notice notice-${tone}`} role={tone === 'danger' ? 'alert' : undefined}>
      <span className="notice-icon">{icon ?? fallback}</span>
      <div>
        {title && <div style={{ fontWeight: 650 }}>{title}</div>}
        {children}
      </div>
    </div>
  )
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline text-secondary-clh" aria-live="polite">
      <Loader2 size={14} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
      {label}
      <style>{'@keyframes spin{to{transform:rotate(360deg)}}'}</style>
    </span>
  )
}

export function HonestyNote({ children }: { children: ReactNode }) {
  return (
    <div className="honesty-note">
      <Info size={13} style={{ marginTop: 1, flex: 'none' }} />
      <span>{children}</span>
    </div>
  )
}

export function MetaItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="meta-item">
      <div className="meta-label">{label}</div>
      <div className="meta-value">{value}</div>
    </div>
  )
}

export function ProgressBar({ value, tone = 'blue' }: { value: number; tone?: 'blue' | 'green' | 'amber' }) {
  const colour =
    tone === 'green' ? 'var(--clh-success)' : tone === 'amber' ? 'var(--clh-warning)' : 'var(--clh-primary)'
  return (
    <div style={{ height: 6, background: 'var(--clh-border)', borderRadius: 999, overflow: 'hidden' }}>
      <div
        style={{
          width: `${Math.max(0, Math.min(100, value))}%`,
          height: '100%',
          background: colour,
          borderRadius: 999,
        }}
      />
    </div>
  )
}

/* ------------------------------------------------------- permission states */
export function PermissionDenied({
  title = 'You do not have access to this project',
  description = 'Your account is signed in, but it is not a member of this research project. Ask a project owner or a workspace administrator to grant access.',
  action,
}: {
  title?: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="empty-state" role="alert">
      <div className="empty-icon">
        <ShieldAlert size={18} />
      </div>
      <div className="empty-title">{title}</div>
      <div className="empty-description">{description}</div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  )
}
