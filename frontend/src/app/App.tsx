import { Navigate, Route, Routes } from 'react-router-dom'
import { useSession } from './SessionProvider'
import { AppShell } from '../layouts/AppShell'
import { LoginPage } from '../pages/LoginPage'
import { DashboardPage } from '../pages/DashboardPage'
import { ProjectsPage } from '../pages/ProjectsPage'
import { ProjectNewPage } from '../pages/ProjectNewPage'
import { ProjectDetailPage } from '../pages/ProjectDetailPage'
import { ParticipantsPage } from '../pages/ParticipantsPage'
import { ParticipantDetailPage } from '../pages/ParticipantDetailPage'
import { RecruitmentPage } from '../pages/RecruitmentPage'
import { InterviewsPage } from '../pages/InterviewsPage'
import { InterviewDetailPage } from '../pages/InterviewDetailPage'
import { EvidencePage } from '../pages/EvidencePage'
import { EvidenceDetailPage } from '../pages/EvidenceDetailPage'
import { InsightsPage } from '../pages/InsightsPage'
import { InsightDetailPage } from '../pages/InsightDetailPage'
import { DecisionsPage } from '../pages/DecisionsPage'
import { DecisionDetailPage } from '../pages/DecisionDetailPage'
import { ActionsPage } from '../pages/ActionsPage'
import { AnalyticsPage } from '../pages/AnalyticsPage'
import { SettingsPage } from '../pages/SettingsPage'
import { NotFoundPage } from '../pages/NotFoundPage'
import { LoadingScreen, SessionProblem } from '../pages/LoginPage'

export function App() {
  const { user, isLoading, error, refetchSession } = useSession()

  if (isLoading) return <LoadingScreen />
  if (error) return <SessionProblem error={error} onRetry={refetchSession} />
  if (!user) return <LoginPage />

  return (
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
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/insights/:insightId" element={<InsightDetailPage />} />
        <Route path="/decisions" element={<DecisionsPage />} />
        <Route path="/decisions/:decisionId" element={<DecisionDetailPage />} />
        <Route path="/actions" element={<ActionsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
