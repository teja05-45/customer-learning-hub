import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  BarChart3,
  Bell,
  CalendarDays,
  ChevronRight,
  FolderKanban,
  LayoutDashboard,
  Lightbulb,
  LogOut,
  Menu,
  Quote,
  Scale,
  Search,
  Settings,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import { api } from '../services/api'
import type { Dashboard } from '../types'
import { useSession } from '../app/SessionProvider'
import { GlobalSearch } from '../components/GlobalSearch'
import { relativeTime } from '../utils/format'

const BREADCRUMB_LABELS: Record<string, string> = {
  overview: 'Overview',
  projects: 'Research projects',
  new: 'New project',
  participants: 'Participants',
  recruitment: 'Recruitment',
  interviews: 'Interviews',
  evidence: 'Evidence',
  insights: 'Insights library',
  decisions: 'Decisions & actions',
  actions: 'Actions',
  analytics: 'Analytics',
  settings: 'Settings',
}

export function AppShell() {
  const { user, leave, isDemo } = useSession()
  const location = useLocation()
  const navigate = useNavigate()
  const [searchOpen, setSearchOpen] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)

  useEffect(() => {
    setMobileOpen(false)
    setNotificationsOpen(false)
    setProfileOpen(false)
  }, [location.pathname])

  useEffect(() => {
    const handler = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [])

  const { data: dashboard } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get<Dashboard>('/dashboard'),
    staleTime: 30_000,
    enabled: Boolean(user),
  })

  const breadcrumbs = useMemo(() => {
    const parts = location.pathname.split('/').filter(Boolean)
    return parts.map((part, index) => {
      const isLast = index === parts.length - 1
      const label = BREADCRUMB_LABELS[part] ?? (isLast ? 'Detail' : '—')
      const href = `/${parts.slice(0, index + 1).join('/')}`
      return { label, href, isLast }
    })
  }, [location.pathname])

  const navItems = [
    { to: '/overview', label: 'Overview', icon: LayoutDashboard },
    { to: '/projects', label: 'Research projects', icon: FolderKanban },
    { to: '/participants', label: 'Participants', icon: Users },
    { to: '/recruitment', label: 'Recruitment', icon: UserPlus },
    { to: '/interviews', label: 'Interviews', icon: CalendarDays },
    { to: '/evidence', label: 'Evidence', icon: Quote },
    {
      to: '/insights',
      label: 'Insights library',
      icon: Lightbulb,
      count: dashboard?.insights_awaiting_review ?? undefined,
    },
    {
      to: '/decisions',
      label: 'Decisions & actions',
      icon: Scale,
      count: dashboard?.open_actions ?? undefined,
    },
    { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  ]

  const overdue = dashboard?.outstanding_actions.filter((action) => action.is_overdue) ?? []

  return (
    <div className="app-shell">
      {/* Keyboard users land here first: one Tab past the skip link avoids 12 nav links. */}
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <aside className={`sidebar${mobileOpen ? ' open' : ''}`} aria-label="Primary navigation">
        <div className="sidebar-brand">
          <div className="brand-mark">CL</div>
          <div style={{ minWidth: 0 }}>
            <div className="brand-name">Customer Learning Hub</div>
            <div className="brand-sub">Everyday Goods</div>
          </div>
          <button
            type="button"
            className="icon-button mobile-only"
            style={{ marginLeft: 'auto' }}
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X size={16} />
          </button>
        </div>

        <div className="sidebar-scroll">
          <div className="nav-section-label">Research workspace</div>
          <nav className="sidebar-nav">
            {navItems.slice(0, 5).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <item.icon size={16} className="nav-icon" />
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="nav-section-label">Learning</div>
          <nav className="sidebar-nav">
            {navItems.slice(5).map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
              >
                <item.icon size={16} className="nav-icon" />
                {item.label}
                {item.count ? <span className="nav-count">{item.count}</span> : null}
              </NavLink>
            ))}
          </nav>

          <div className="nav-section-label">Organisation</div>
          <nav className="sidebar-nav">
            <NavLink to="/settings" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <Settings size={16} className="nav-icon" />
              Settings
            </NavLink>
          </nav>
        </div>

        <div className="sidebar-footer">
          {isDemo && (
            <div className="demo-chip">
              <span style={{ fontWeight: 700, flex: 'none' }}>DEMO</span>
              <span>
                Synthetic data only. Outreach, consent and recording are simulated — no customer is contacted and no
                audio is captured.
              </span>
            </div>
          )}
        </div>
      </aside>

      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.3)', zIndex: 29 }}
          aria-hidden="true"
        />
      )}

      <div className="main-column">
        <header className="topbar">
          <button
            type="button"
            className="icon-button mobile-only"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu size={18} />
          </button>

          <nav className="breadcrumbs" aria-label="Breadcrumb">
            <Link to="/overview">Home</Link>
            {breadcrumbs.map((crumb) => (
              <span key={crumb.href} className="inline">
                <ChevronRight size={12} />
                {crumb.isLast ? (
                  <span style={{ color: 'var(--clh-text)' }}>{crumb.label}</span>
                ) : (
                  <Link to={crumb.href}>{crumb.label}</Link>
                )}
              </span>
            ))}
          </nav>

          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              type="button"
              className="search-trigger"
              onClick={() => setSearchOpen(true)}
              aria-keyshortcuts="Control+K Meta+K"
            >
              <Search size={14} />
              <span className="search-label" style={{ flex: 1, textAlign: 'left' }}>
                Search
              </span>
              <span className="kbd">⌘K</span>
            </button>

            <div style={{ position: 'relative' }}>
              <button
                type="button"
                className="icon-button"
                aria-label="Notifications"
                aria-expanded={notificationsOpen}
                onClick={() => {
                  setNotificationsOpen((open) => !open)
                  setProfileOpen(false)
                }}
              >
                <Bell size={17} />
                {overdue.length > 0 && (
                  <span
                    style={{
                      position: 'absolute',
                      top: 3,
                      right: 4,
                      width: 7,
                      height: 7,
                      borderRadius: 99,
                      background: 'var(--clh-danger)',
                    }}
                  />
                )}
              </button>
              {notificationsOpen && (
                <div
                  className="card-surface"
                  style={{ position: 'absolute', right: 0, top: 38, width: 330, zIndex: 40, overflow: 'hidden' }}
                >
                  <div className="card-header-row" style={{ padding: '11px 14px' }}>
                    <div>
                      <div className="card-title">Needs attention</div>
                      <div className="card-subtitle">Overdue follow-ups and review queues</div>
                    </div>
                  </div>
                  <div style={{ padding: 8 }}>
                    {overdue.length === 0 && (
                      <div className="definition" style={{ padding: 10 }}>
                        Nothing overdue. Open actions appear here when their due date passes.
                      </div>
                    )}
                    {overdue.map((action) => (
                      <Link
                        key={action.id}
                        to="/actions"
                        className="command-result"
                        style={{ display: 'block' }}
                      >
                        <div className="command-result-title">{action.title}</div>
                        <div className="command-result-sub">
                          {action.code} · due {relativeTime(action.due_date)} · {action.owner?.label ?? 'Unassigned'}
                        </div>
                      </Link>
                    ))}
                    {(dashboard?.insights_awaiting_review ?? 0) > 0 && (
                      <Link to="/insights" className="command-result" style={{ display: 'block' }}>
                        <div className="command-result-title">
                          {dashboard?.insights_awaiting_review} insight(s) awaiting review
                        </div>
                        <div className="command-result-sub">Draft or under review — nobody has signed them off</div>
                      </Link>
                    )}
                  </div>
                </div>
              )}
            </div>

            <div style={{ position: 'relative' }}>
              <button
                type="button"
                className="profile-button"
                onClick={() => {
                  setProfileOpen((open) => !open)
                  setNotificationsOpen(false)
                }}
                aria-expanded={profileOpen}
              >
                <span className="avatar">{user?.initials ?? '—'}</span>
                <span className="hide-sm">{user?.name ?? 'Not signed in'}</span>
              </button>
              {profileOpen && (
                <div
                  className="card-surface"
                  style={{ position: 'absolute', right: 0, top: 40, width: 268, zIndex: 40, overflow: 'hidden' }}
                >
                  <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--clh-border)' }}>
                    <div style={{ fontWeight: 650, fontSize: 13 }}>{user?.name}</div>
                    <div className="definition">{user?.job_title}</div>
                    <div className="notice notice-warning mt-2" style={{ padding: '6px 8px' }}>
                      <span className="notice-icon">DEMO</span>
                      <span style={{ fontSize: 11 }}>
                        Role switching is a demonstration feature, not authentication.
                      </span>
                    </div>
                  </div>
                  <div style={{ padding: 6 }}>
                    <button
                      type="button"
                      className="command-result"
                      onClick={() => navigate('/settings')}
                      style={{ display: 'flex', gap: 8, alignItems: 'center' }}
                    >
                      <Settings size={14} /> Settings
                    </button>
                    <button
                      type="button"
                      className="command-result"
                      onClick={() => {
                        leave()
                        navigate('/')
                      }}
                      style={{ display: 'flex', gap: 8, alignItems: 'center' }}
                    >
                      <LogOut size={14} /> Switch demonstration role
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        <main id="main" tabIndex={-1}>
          <Outlet />
        </main>
      </div>

      <GlobalSearch open={searchOpen} onClose={() => setSearchOpen(false)} />
    </div>
  )
}
