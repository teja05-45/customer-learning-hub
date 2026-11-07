import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useSession } from './SessionProvider'
import { AppShell } from '../layouts/AppShell'
import { ProjectProvider } from './ProjectProvider'
import { LoginPage } from '../pages/LoginPage'
import { LoadingScreen, SessionProblem } from '../pages/LoginPage'

// Route-level code splitting keeps the first payload small. The dashboard is the
// landing screen and is loaded with the shell; every other screen is fetched on
// first navigation. Named exports are adapted at the boundary.
const DashboardPage = lazy(() => import('../pages/DashboardPage').then((m) => ({ default: m.DashboardPage })))
const ProjectsPage = lazy(() => import('../pages/ProjectsPage').then((m) => ({ default: m.ProjectsPage })))
const ProjectNewPage = lazy(() => import('../pages/ProjectNewPage').then((m) => ({ default: m.ProjectNewPage })))
const ProjectDetailPage = lazy(() =>
  import('../pages/ProjectDetailPage').then((m) => ({ default: m.ProjectDetailPage })),
)
const ParticipantsPage = lazy(() =>
  import('../pages/ParticipantsPage').then((m) => ({ default: m.ParticipantsPage })),
)
const ParticipantDetailPage = lazy(() =>
  import('../pages/ParticipantDetailPage').then((m) => ({ default: m.ParticipantDetailPage })),
)
const RecruitmentPage = lazy(() =>
  import('../pages/RecruitmentPage').then((m) => ({ default: m.RecruitmentPage })),
)
const InterviewsPage = lazy(() =>
  import('../pages/InterviewsPage').then((m) => ({ default: m.InterviewsPage })),
)
const InterviewDetailPage = lazy(() =>
  import('../pages/InterviewDetailPage').then((m) => ({ default: m.InterviewDetailPage })),
)
const EvidencePage = lazy(() => import('../pages/EvidencePage').then((m) => ({ default: m.EvidencePage })))
const EvidenceDetailPage = lazy(() =>
  import('../pages/EvidenceDetailPage').then((m) => ({ default: m.EvidenceDetailPage })),
)
const FeedbackPage = lazy(() => import('../pages/FeedbackPage').then((m) => ({ default: m.FeedbackPage })))
const InsightsPage = lazy(() => import('../pages/InsightsPage').then((m) => ({ default: m.InsightsPage })))
const InsightDetailPage = lazy(() =>
  import('../pages/InsightDetailPage').then((m) => ({ default: m.InsightDetailPage })),
)
const DecisionsPage = lazy(() => import('../pages/DecisionsPage').then((m) => ({ default: m.DecisionsPage })))
const DecisionDetailPage = lazy(() =>
  import('../pages/DecisionDetailPage').then((m) => ({ default: m.DecisionDetailPage })),
)
const ActionsPage = lazy(() => import('../pages/ActionsPage').then((m) => ({ default: m.ActionsPage })))
const OutcomesPage = lazy(() => import('../pages/OutcomesPage').then((m) => ({ default: m.OutcomesPage })))
const AnalyticsPage = lazy(() => import('../pages/AnalyticsPage').then((m) => ({ default: m.AnalyticsPage })))
const SettingsPage = lazy(() => import('../pages/SettingsPage').then((m) => ({ default: m.SettingsPage })))
const NotFoundPage = lazy(() => import('../pages/NotFoundPage').then((m) => ({ default: m.NotFoundPage })))

export function App() {
  const { user, isLoading, error, refetchSession } = useSession()

  if (isLoading) return <LoadingScreen />
  if (error) return <SessionProblem error={error} onRetry={refetchSession} />
  if (!user) return <LoginPage />

  return (
    <Suspense fallback={<LoadingScreen />}>
      <ProjectProvider>
        <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<DashboardPage />} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/new" element={<ProjectNewPage />} />
          <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
          <Route path="/participants" element={<ParticipantsPage />} />
          <Route path="/participants/:participantId" element={<ParticipantDetailPage />} />
          <Route path="/recruitment" element={<RecruitmentPage />} />
          <Route path="/interviews" element={<InterviewsPage />} />
          <Route path="/interviews/:interviewId" element={<InterviewDetailPage />} />
          <Route path="/evidence" element={<EvidencePage />} />
          <Route path="/evidence/:evidenceId" element={<EvidenceDetailPage />} />
          <Route path="/feedback" element={<FeedbackPage />} />
          <Route path="/insights" element={<InsightsPage />} />
          <Route path="/insights/:insightId" element={<InsightDetailPage />} />
          <Route path="/decisions" element={<DecisionsPage />} />
          <Route path="/decisions/:decisionId" element={<DecisionDetailPage />} />
          <Route path="/actions" element={<ActionsPage />} />
          <Route path="/outcomes" element={<OutcomesPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </ProjectProvider>
    </Suspense>
  )
}
