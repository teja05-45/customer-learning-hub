import { ShieldCheck, ArrowRight, Quote, Link2, ListChecks } from 'lucide-react'
import { useSession } from '../app/SessionProvider'
import { errorMessage } from '../services/api'
import { Spinner } from '../components/ui'
import { titleCase } from '../utils/format'

export function LoadingScreen() {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--clh-bg)' }}>
      <div className="stack stack-3" style={{ alignItems: 'center' }}>
        <div className="brand-mark" style={{ width: 38, height: 38, fontSize: 15 }}>
          CL
        </div>
        <Spinner label="Loading the research workspace…" />
      </div>
    </div>
  )
}

export function SessionProblem({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', background: 'var(--clh-bg)', padding: 24 }}>
      <div className="card-surface card-section" style={{ maxWidth: 460 }}>
        <div className="card-title" style={{ fontSize: 15 }}>
          The API is not responding
        </div>
        <p className="page-description mt-2">
          {errorMessage(error)} Start the backend with{' '}
          <span className="mono">uvicorn app.main:app --port 8000</span> from the <span className="mono">backend</span>{' '}
          directory, then retry.
        </p>
        <button type="button" className="btn btn-primary mt-2" onClick={onRetry}>
          Retry connection
        </button>
      </div>
    </div>
  )
}

const VALUE_POINTS = [
  {
    icon: Quote,
    title: 'Every insight keeps its source',
    body: 'Customer words, researcher interpretation and provenance are stored separately, so nobody has to guess where a claim came from.',
  },
  {
    icon: Link2,
    title: 'Decisions show their evidence',
    body: 'A decision without a linked customer source is labelled as an internal judgement — not dressed up as research.',
  },
  {
    icon: ListChecks,
    title: 'Someone owns the next step',
    body: 'Recruitment, review and follow-up actions all have a named owner, a due date and a visible state.',
  },
]

export function LoginPage() {
  const { users, session, enter, isLoading } = useSession()

  return (
    <div className="login-shell">
      <aside className="login-aside">
        <div>
          <div className="inline" style={{ gap: 10 }}>
            <div className="brand-mark" style={{ background: '#fff', color: 'var(--clh-navy)' }}>
              CL
            </div>
            <div>
              <div style={{ color: '#fff', fontWeight: 650, fontSize: 13.5 }}>Customer Learning Hub</div>
              <div style={{ color: '#94a3b8', fontSize: 10.5, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                Everyday Goods
              </div>
            </div>
          </div>

          <h1 className="mt-4">Turn customer conversations into decisions you can defend.</h1>
          <p className="mt-3">
            Everyday Goods runs research in the gaps between campaigns and support queues. This workspace gives the
            team one place to plan a study, record what customers actually said, and connect it to a decision with an
            owner.
          </p>

          <div className="login-value-list mt-4">
            {VALUE_POINTS.map((point) => (
              <div className="login-value" key={point.title}>
                <point.icon size={16} style={{ marginTop: 2, flex: 'none', color: '#93b4f5' }} />
                <div>
                  <strong>{point.title}</strong>
                  {point.body}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="login-value" style={{ position: 'relative', zIndex: 1 }}>
          <ShieldCheck size={16} style={{ marginTop: 2, flex: 'none', color: '#93b4f5' }} />
          <div>
            <strong>This prototype contains synthetic data only.</strong>
            No customer is contacted, no Everyday Goods system is connected, and no audio is recorded. Names,
            conversations and outcomes are invented for demonstration.
          </div>
        </div>
      </aside>

      <main className="login-main">
        <div style={{ maxWidth: 460, width: '100%', margin: '0 auto' }}>
          <div className="pill pill-blue">Demonstration entry</div>
          <h2 className="mt-3" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>
            Choose a role to explore the workspace
          </h2>
          <p className="page-description mt-2">
            Each role opens the same shared workspace with a different starting view. No password is required because
            this is a prototype — there is no authentication behind it.
          </p>

          <div className="stack stack-2 mt-3">
            {isLoading && <div className="skeleton" style={{ height: 56 }} />}
            {users.map((user) => (
              <button key={user.id} type="button" className="role-card" onClick={() => enter(user)}>
                <span className="avatar" style={{ width: 32, height: 32, fontSize: 11 }}>
                  {user.initials}
                </span>
                <span style={{ flex: 1 }}>
                  <span className="row-between">
                    <span className="role-name">{user.name}</span>
                    <span className="pill pill-outline">{titleCase(user.role)}</span>
                  </span>
                  <span className="role-desc d-block">{user.description}</span>
                </span>
                <ArrowRight size={15} style={{ marginTop: 8, color: 'var(--clh-text-tertiary)' }} />
              </button>
            ))}
          </div>

          <div className="notice notice-warning mt-4">
            <span className="notice-icon">!</span>
            <div>
              <strong>Role switching is a demonstration feature.</strong> It is not authentication, authorisation or a
              security boundary. Every API request in this prototype is served with the same permissions regardless of
              the role selected.
            </div>
          </div>

          {session?.notice && <div className="definition mt-3">{session.notice}</div>}
        </div>
      </main>
    </div>
  )
}
