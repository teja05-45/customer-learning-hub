import { useState, type FormEvent } from 'react'
import { ShieldCheck, ArrowRight, Quote, Link2, ListChecks, KeyRound } from 'lucide-react'
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
  const { users, session, enter, signIn, isLoading } = useSession()
  const [busyId, setBusyId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [signingIn, setSigningIn] = useState(false)

  const choose = async (user: (typeof users)[number]) => {
    setError(null)
    setBusyId(user.id)
    try {
      await enter(user)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setBusyId(null)
    }
  }

  const submitPassword = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSigningIn(true)
    try {
      await signIn(email.trim(), password)
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setSigningIn(false)
    }
  }

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
          <div className="pill pill-blue">Sign in</div>
          <h2 className="mt-3" style={{ fontSize: 24, letterSpacing: '-0.02em' }}>
            Open the research workspace
          </h2>
          <p className="page-description mt-2">
            Sign in with your email and password, or use a demonstration role when demo mode is enabled. The API
            authorises every write against your role; the role picker is not a security boundary.
          </p>

          <form className="mt-3" onSubmit={submitPassword}>
            <div className="stack stack-2">
              <div>
                <label className="form-label" htmlFor="login-email">
                  Email
                </label>
                <input
                  id="login-email"
                  type="email"
                  className="form-control"
                  autoComplete="username"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                />
              </div>
              <div>
                <label className="form-label" htmlFor="login-password">
                  Password
                </label>
                <input
                  id="login-password"
                  type="password"
                  className="form-control"
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>
              <button type="submit" className="btn btn-primary" disabled={signingIn}>
                <KeyRound size={14} /> {signingIn ? 'Signing in…' : 'Sign in'}
              </button>
            </div>
          </form>

          {error && (
            <div className="notice notice-danger mt-3">
              <span className="notice-icon">!</span>
              <div>{error}</div>
            </div>
          )}

          {session?.demo_mode && (
            <>
              <div className="inline mt-4" style={{ gap: 8 }}>
                <div className="pill pill-outline">Demonstration entry</div>
                <span className="definition">Only available while demo mode is enabled.</span>
              </div>
              <div className="stack stack-2 mt-2">
                {isLoading && <div className="skeleton" style={{ height: 56 }} />}
                {users.map((user) => (
                  <button
                    key={user.id}
                    type="button"
                    className="role-card"
                    onClick={() => void choose(user)}
                    disabled={busyId !== null}
                  >
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
            </>
          )}

          <div className="notice notice-warning mt-4">
            <span className="notice-icon">!</span>
            <div>
              <strong>Demo entry creates a real session, but this is not SSO.</strong> The API enforces role
              permissions on every write. Connecting an identity provider is the remaining production step; see
              docs/AUTH.md.
            </div>
          </div>

          {session?.notice && <div className="definition mt-3">{session.notice}</div>}
        </div>
      </main>
    </div>
  )
}
