import {zodResolver} from '@hookform/resolvers/zod'
import {useMutation, useQuery} from '@tanstack/react-query'
import {Filter, LayoutList, Network, Plus, Search, UsersRound} from 'lucide-react'
import {lazy, Suspense, useCallback, useMemo, useState} from 'react'
import {useForm} from 'react-hook-form'
import {z} from 'zod'
import {queryClient} from '../../lib/query'
import {api} from '../../services/api'
import type {CasePerson, PersonRelationship} from '../../types'
import {PersonDetailsPanel} from './PersonDetailsPanel'
import {PeopleFilters, type PeopleFilter} from './PeopleFilters'
import {PeopleList} from './PeopleList'

const PeopleNetwork = lazy(async () => ({default: (await import('./PeopleNetwork')).PeopleNetwork}))

const EMPTY_PEOPLE: CasePerson[] = []
const EMPTY_RELATIONSHIPS: PersonRelationship[] = []
const personSchema = z.object({
    name: z.string().trim().min(2).max(240),
    role: z.string().trim().min(2).max(120),
    category: z.enum(['primary', 'family', 'friend', 'law_enforcement', 'witness', 'other']),
    entity_type: z.enum(['person', 'organization', 'location', 'other']),
    summary: z.string().trim().max(5000)
})
type PersonForm = z.infer<typeof personSchema>

export function PeoplePanel({caseId, readOnly = false}: { caseId: string; readOnly?: boolean }) {
    const [filter, setFilter] = useState<PeopleFilter>('all')
    const [search, setSearch] = useState('')
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [inspectedRelationship, setInspectedRelationship] = useState<PersonRelationship | null>(null)
    const [view, setView] = useState<'network' | 'list'>('network')
    const [creating, setCreating] = useState(false)
    const peopleQuery = useQuery({queryKey: ['case', caseId, 'people'], queryFn: () => api.people(caseId)})
    const relationshipQuery = useQuery({
        queryKey: ['case', caseId, 'relationships'],
        queryFn: () => api.relationships(caseId)
    })
    const people = peopleQuery.data ?? EMPTY_PEOPLE
    const relationships = relationshipQuery.data ?? EMPTY_RELATIONSHIPS
    const visiblePeople = useMemo(() => people.filter((person) => {
        const matchesFilter = filter === 'all' || person.category === filter
        const term = search.trim().toLowerCase()
        return matchesFilter && (!term || `${person.name} ${person.role} ${person.summary ?? ''}`.toLowerCase().includes(term))
    }), [people, filter, search])
    const selected = people.find((person) => person.id === selectedId) ?? null
    const select = useCallback((id: string) => {
        setSelectedId(id)
        setInspectedRelationship(null)
    }, [])
    const inspectRelationship = useCallback((relationship: PersonRelationship) => {
        setSelectedId(relationship.source_person_id)
        setInspectedRelationship(relationship)
    }, [])

    if (peopleQuery.isLoading || relationshipQuery.isLoading) return <div
        className="card grid min-h-[480px] place-items-center">
        <div className="text-center"><span
            className="mx-auto block size-7 animate-spin rounded-full border-2 border-subtle border-t-accent"/><p
            className="mt-4 text-xs text-muted">Mapping people and relationships…</p></div>
    </div>
    if (peopleQuery.isError || relationshipQuery.isError) return <div className="error-banner min-h-28"><p
        className="font-semibold">The relationship workspace could not be loaded.</p>
        <button type="button" onClick={() => {
            peopleQuery.refetch();
            relationshipQuery.refetch()
        }} className="secondary-button mt-3 text-xs">Try again
        </button>
    </div>

    return <section>
        <header className="flex flex-col gap-5 border-b border-subtle pb-5 xl:flex-row xl:items-end xl:justify-between">
            <div><p className="eyebrow">Case intelligence</p><h2
                className="page-title mt-2">People &amp; Relationships</h2><p
                className="mt-2 text-[15px] text-secondary">Key individuals, their connections, and how they relate to
                this case.</p></div>
            <div className="flex w-full gap-2 xl:w-auto"><label
                className="relative block min-w-0 flex-1 xl:w-80"><Search size={16}
                                                                          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"/><input
                value={search} onChange={(event) => setSearch(event.target.value)} className="field pl-10"
                placeholder="Search people…"/><span className="sr-only">Search people</span></label>
                {!readOnly && <button type="button" onClick={() => setCreating((value) => !value)}
                        className="primary-button shrink-0 text-xs"><Plus size={15}/>{creating ? 'Close' : 'Add person'}
                </button>}
            </div>
        </header>

        {creating && <CreatePersonForm caseId={caseId} onCreated={(id) => {
            setCreating(false);
            setSelectedId(id)
        }}/>}

        {people.length > 0 && <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
            <div className="lg:hidden"><PeopleFilters people={people} value={filter} onChange={setFilter} mobile/></div>
            <div className="ml-auto inline-flex rounded-lg border border-default bg-surface p-1" aria-label="People view">
                <button type="button" onClick={() => setView('network')} aria-pressed={view === 'network'} className={`ghost-button min-h-9 px-3 text-xs ${view === 'network' ? 'bg-accent-muted text-accent' : ''}`}><Network size={14}/>Network</button>
                <button type="button" onClick={() => setView('list')} aria-pressed={view === 'list'} className={`ghost-button min-h-9 px-3 text-xs ${view === 'list' ? 'bg-accent-muted text-accent' : ''}`}><LayoutList size={14}/>List</button>
            </div>
        </div>}
        {!people.length ? !creating && <div className="card mt-5 grid min-h-[430px] place-items-center p-8 text-center">
            <div><UsersRound size={34} className="mx-auto text-muted"/><h3 className="empty-title mt-4">No people mapped
                yet</h3><p className="mx-auto mt-2 max-w-md font-display text-lg text-secondary">Relationships become
                visible as sourced people and organizations are added to the case.</p><p
                className="mt-3 text-xs text-muted">Add a standalone person now. A relationship is optional.</p></div>
        </div> : <div
            className="mt-5 grid gap-4 lg:grid-cols-[180px_minmax(0,1fr)_300px] xl:grid-cols-[190px_minmax(0,1fr)_320px]">
            <div className="hidden lg:block">
                <div className="sticky top-20"><PeopleFilters people={people} value={filter} onChange={setFilter}/>
                </div>
            </div>
            <main className="min-w-0">{!visiblePeople.length ?
                <div className="card grid min-h-[420px] place-items-center p-8 text-center">
                    <div><Filter className="mx-auto text-muted"/><h3 className="empty-title mt-4">No matching
                        people</h3><p className="mt-2 text-sm text-muted">Adjust the category filter or search
                        terms.</p></div>
                </div> : view === 'network' ? <Suspense fallback={<div className="card h-[520px] animate-pulse lg:h-[640px]"/>}><PeopleNetwork people={visiblePeople} relationships={relationships} selectedId={selectedId} onSelect={select} onInspectRelationship={inspectRelationship}/></Suspense> : <PeopleList people={visiblePeople} onSelect={select}/>}</main>
            <aside className="hidden lg:block">
                <div className="sticky top-20"><PersonDetailsPanel caseId={caseId} person={selected} people={people}
                                                                   relationships={relationships}
                                                                   inspectedRelationship={inspectedRelationship} onSelect={select} readOnly={readOnly}/>
                </div>
            </aside>
        </div>}

        {selected && <div className="fixed inset-0 z-40 bg-background/60 backdrop-blur-[2px] lg:hidden"
                          onClick={() => setSelectedId(null)}>
            <div
                className="absolute inset-x-0 bottom-0 max-h-[86dvh] overflow-y-auto rounded-t-2xl border border-subtle bg-elevated p-3 shadow-[0_-16px_50px_rgba(0,0,0,.45)]"
                onClick={(event) => event.stopPropagation()}>
                <div className="mx-auto mb-3 h-1 w-10 rounded-full bg-default"/>
                <PersonDetailsPanel caseId={caseId} person={selected} people={people} relationships={relationships}
                                    inspectedRelationship={inspectedRelationship} onSelect={select} onClose={() => {setSelectedId(null); setInspectedRelationship(null)}} readOnly={readOnly}/>
            </div>
        </div>}
    </section>
}

function CreatePersonForm({caseId, onCreated}: { caseId: string; onCreated: (id: string) => void }) {
    const form = useForm<PersonForm>({
        resolver: zodResolver(personSchema),
        defaultValues: {category: 'other', entity_type: 'person', summary: ''}
    })
    const create = useMutation({
        mutationFn: (data: PersonForm) => api.createPerson(caseId, {
            ...data,
            summary: data.summary || undefined
        }), onSuccess: async (person) => {
            await queryClient.invalidateQueries({queryKey: ['case', caseId, 'people']});
            onCreated(person.id)
        }
    })
    return <form onSubmit={form.handleSubmit((data) => create.mutate(data))}
                 className="card mt-5 border-default p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2"><label className="text-xs font-semibold text-primary">Name<input
            className="field mt-2"
            placeholder="Full public name" {...form.register('name')}/>{form.formState.errors.name &&
            <span className="mt-1 block text-xs text-danger">Enter a name</span>}</label><label
            className="text-xs font-semibold text-primary">Role in case<input className="field mt-2"
                                                                              placeholder="Witness, family member, agency…" {...form.register('role')}/>{form.formState.errors.role &&
            <span className="mt-1 block text-xs text-danger">Enter a role</span>}</label><label
            className="text-xs font-semibold text-primary">Category<select
            className="field mt-2" {...form.register('category')}>
            <option value="primary">Primary</option>
            <option value="family">Family</option>
            <option value="friend">Friend</option>
            <option value="law_enforcement">Law enforcement</option>
            <option value="witness">Witness</option>
            <option value="other">Other</option>
        </select></label><label className="text-xs font-semibold text-primary">Entity type<select
            className="field mt-2" {...form.register('entity_type')}>
            <option value="person">Person</option>
            <option value="organization">Organization</option>
            <option value="location">Location entity</option>
            <option value="other">Other</option>
        </select></label></div>
        <label className="mt-4 block text-xs font-semibold text-primary">Case summary (optional)<textarea
            className="field mt-2 min-h-24 resize-y py-3"
            placeholder="Describe their known role without making unsupported claims." {...form.register('summary')}/></label>{create.error &&
        <p role="alert" className="mt-3 text-xs text-danger">The person could not be added.</p>}
        <button disabled={create.isPending} className="primary-button mt-4 text-xs"><Plus
            size={15}/>{create.isPending ? 'Adding…' : 'Add person'}</button>
        <p className="metadata mt-3 text-[10px]">This person can exist independently and may be linked to events,
            discussions, locations, or evidence later.</p></form>
}
