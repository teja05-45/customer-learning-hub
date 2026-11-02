import { Link, useLocation } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { EmptyState, PageHeader, SectionCard } from '../components/ui'

export function NotFoundPage() {
  const location = useLocation()

  return (
    <div className="page">
      <PageHeader title="Page not found" description="That route does not exist in this workspace." />
      <SectionCard>
        <EmptyState
          icon={<Compass size={18} />}
          title={`Nothing at ${location.pathname}`}
          description="The link may be out of date, or the record may have been archived. Use search to find the project or insight you were looking for."
          action={
            <Link to="/overview" className="btn btn-primary btn-sm">
              Back to overview
            </Link>
          }
        />
      </SectionCard>
    </div>
  )
}
