import { useQuery } from '@tanstack/react-query'
import { BriefcaseBusiness, Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router'
import { EmptyState, PageHeader } from '../../components/ui/Visual'
import { api } from '../../services/api'
import { CaseCard } from './CaseCard'

export function MyCasesPage() {
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['cases', 'mine'],
    queryFn: api.myCases,
  })

  return <div>
    <div className="flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <PageHeader
        eyebrow="Owned investigations"
        title="My cases"
        description="Cases you created and control, including private investigations."
      />
      <Link to="/cases/new" className="primary-button shrink-0 px-5"><Plus size={16}/> New case</Link>
    </div>

    {isLoading
      ? <div className="grid min-h-64 place-items-center"><Sparkles className="animate-pulse text-accent"/></div>
      : cases.length
        ? <div className="mt-8 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{cases.map((item) => <CaseCard key={item.id} item={item}/>)}</div>
        : <div className="mt-8"><EmptyState icon={BriefcaseBusiness} title="You haven’t created a case yet">Create a public or private investigation to begin building its overview, timeline, evidence, locations, and people.</EmptyState></div>}
  </div>
}
