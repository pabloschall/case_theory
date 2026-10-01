import { ChevronLeft, ChevronRight, Clock3, FileSearch, MessageSquare, Plus, Search, Sparkles } from 'lucide-react'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link } from 'react-router'
import { api } from '../../services/api'
import { EmptyState, SectionHeader } from '../../components/ui/Visual'
import { CaseCard } from '../cases/CaseCard'

type CaseSort = 'newest' | 'popular'

export function HomePage() {
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [sort, setSort] = useState<CaseSort>('newest')
  const [page, setPage] = useState(1)
  const { data: currentUser } = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser, retry: false })
  const { data, isFetching } = useQuery({
    queryKey: ['cases', 'directory', search, sort, page],
    queryFn: () => api.searchCases(search, sort, page),
    placeholderData: keepPreviousData,
  })
  const results = data?.items ?? []
  const submit = (event: FormEvent) => { event.preventDefault(); setPage(1); setSearch(input.trim()) }
  const changeSort = (nextSort: CaseSort) => { setPage(1); setSort(nextSort) }

  return <div>
    <section className="surface relative overflow-hidden">
      <div className="absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(circle_at_top_right,rgba(106,155,196,.12),transparent_68%)]" />
      <div className="relative p-6 sm:p-8 lg:p-10">
        <p className="eyebrow">Case directory</p>
        <h1 className="page-title mt-5 max-w-3xl sm:text-5xl">Explore public investigations.</h1>
        <p className="mt-5 max-w-xl text-[15px] leading-7 text-secondary">Search sourced public cases by name, year, or location, then inspect the timeline, evidence, discussion, map, and people connected to each investigation.</p>
        <form onSubmit={submit} className="mt-8 flex max-w-xl flex-col gap-2 sm:flex-row"><label className="relative flex-1"><span className="sr-only">Search public cases</span><Search className="absolute left-4 top-1/2 -translate-y-1/2 text-muted" size={18}/><input value={input} onChange={(event) => setInput(event.target.value)} className="field pl-12" placeholder="Search name, year, or location" /></label><button className="primary-button px-6">Search cases</button></form>
      </div>
    </section>

    <section className="mt-9">
      <SectionHeader eyebrow="Public investigations" title={search ? `Results for “${search}”` : 'All public cases'} action={currentUser ? <Link to="/cases/new" className="secondary-button text-xs text-accent"><Plus size={16}/> Create case</Link> : <Link to="/login" className="secondary-button text-xs text-accent">Sign in to contribute</Link>}/>
      <div className="mt-5 flex flex-col gap-3 border-b border-subtle pb-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-muted">{isFetching ? 'Updating directory…' : `${data?.total ?? 0} ${(data?.total ?? 0) === 1 ? 'case' : 'cases'}`}</p>
        <div className="inline-flex w-full rounded-lg border border-default bg-background/50 p-1 sm:w-auto" aria-label="Sort cases">
          <button type="button" onClick={() => changeSort('newest')} className={`flex min-h-10 flex-1 items-center justify-center gap-2 rounded-md px-4 text-xs font-semibold transition sm:flex-none ${sort === 'newest' ? 'bg-accent-muted text-accent' : 'text-muted hover:text-primary'}`}><Clock3 size={15}/>Recently created</button>
          <button type="button" onClick={() => changeSort('popular')} className={`flex min-h-10 flex-1 items-center justify-center gap-2 rounded-md px-4 text-xs font-semibold transition sm:flex-none ${sort === 'popular' ? 'bg-accent-muted text-accent' : 'text-muted hover:text-primary'}`}><MessageSquare size={15}/>Most discussed</button>
        </div>
      </div>
      {results.length ? <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{results.map((item) => <CaseCard key={item.id} item={item} showFollow={Boolean(currentUser)}/>)}</div> : <div className="mt-5"><EmptyState icon={FileSearch} title="No public cases found">Try a different name, year, or location.</EmptyState></div>}
      {data && data.total_pages > 1 && <nav className="mt-7 flex items-center justify-between gap-3" aria-label="Case directory pages">
        <button type="button" className="secondary-button min-w-0 px-3 sm:px-4" disabled={!data.has_previous || isFetching} onClick={() => setPage((value) => Math.max(1, value - 1))}><ChevronLeft size={16}/> Previous</button>
        <span className="metadata text-center">Page {data.page} of {data.total_pages}</span>
        <button type="button" className="secondary-button min-w-0 px-3 sm:px-4" disabled={!data.has_next || isFetching} onClick={() => setPage((value) => value + 1)}>Next <ChevronRight size={16}/></button>
      </nav>}
      {isFetching && <Sparkles className="fixed bottom-24 right-5 animate-pulse text-accent md:bottom-6" size={18}/>} 
    </section>
  </div>
}
