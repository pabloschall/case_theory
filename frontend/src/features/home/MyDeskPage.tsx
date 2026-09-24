import { useQuery } from '@tanstack/react-query'
import { Bookmark, Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router'
import { EmptyState, PageHeader } from '../../components/ui/Visual'
import { api } from '../../services/api'
import { CaseCard } from '../cases/CaseCard'

export function MyDeskPage() {
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['cases', 'following'],
    queryFn: api.followingCases,
  })

  return <div>
    <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <PageHeader
        eyebrow="Your workspace"
        title="My Desk"
        description="The cases you follow or collaborate on, gathered in one focused research workspace."
      />
      <Link to="/cases/new" className="primary-button shrink-0 px-5"><Plus size={16}/> New case</Link>
    </div>

    {isLoading
      ? <div className="grid min-h-64 place-items-center"><Sparkles className="animate-pulse text-accent"/></div>
      : cases.length
        ? <div className="mt-8 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{cases.map((item) => <CaseCard key={item.id} item={item}/>)}</div>
        : <div className="mt-8"><EmptyState icon={Bookmark} title="Your desk is ready">Open a case from the directory to begin following its investigation.</EmptyState></div>}
  </div>
}
