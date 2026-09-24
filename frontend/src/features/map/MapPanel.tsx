import {zodResolver} from '@hookform/resolvers/zod'
import {useMutation, useQuery} from '@tanstack/react-query'
import {Check, ExternalLink, LocateFixed, MapPinned, Plus, Search, Sparkles, X} from 'lucide-react'
import {useMemo, useState} from 'react'
import type {ReactNode} from 'react'
import {useForm} from 'react-hook-form'
import {z} from 'zod'
import {queryClient} from '../../lib/query'
import {ApiError, api} from '../../services/api'
import type {CaseLocation, LocationType} from '../../types'
import {EvidenceCard} from '../evidence/EvidenceCard'
import {EvidencePicker} from '../evidence/EvidencePicker'
import {LinkedPeople, PersonPicker} from '../people/PersonPicker'
import {UpgradeButton} from '../../components/ui/Visual'

const locationTypes: { value: LocationType; label: string; color: string }[] = [
    {value: 'primary', label: 'Primary location', color: 'bg-accent'},
    {value: 'event', label: 'Case event', color: 'bg-teal'},
    {value: 'evidence', label: 'Evidence', color: 'bg-blue'},
    {value: 'last_seen', label: 'Last seen', color: 'bg-danger'},
    {value: 'sighting', label: 'Reported sighting', color: 'bg-warning'},
    {value: 'search_area', label: 'Search area', color: 'bg-purple'},
    {value: 'law_enforcement', label: 'Law enforcement', color: 'bg-purple'},
    {value: 'other', label: 'Other', color: 'bg-muted'},
]
const typeConfig = Object.fromEntries(locationTypes.map((item) => [item.value, item])) as Record<LocationType, (typeof locationTypes)[number]>

const locationSchema = z.object({
    name: z.string().trim().min(2, 'Add a location name').max(240),
    description: z.string().trim().min(3, 'Explain why this location matters').max(3000),
    latitude: z.number().min(-90, 'Latitude must be between -90 and 90').max(90, 'Latitude must be between -90 and 90'),
    longitude: z.number().min(-180, 'Longitude must be between -180 and 180').max(180, 'Longitude must be between -180 and 180'),
    location_type: z.enum(['primary', 'event', 'evidence', 'last_seen', 'sighting', 'search_area', 'law_enforcement', 'other']),
    occurred_on: z.union([z.literal(''), z.iso.date('Choose a valid date')]),
    precision: z.enum(['exact', 'approximate']),
    verification_status: z.enum(['verified', 'source_backed', 'unverified', 'disputed']),
    source_url: z.union([z.literal(''), z.url('Enter a valid source URL')]),
})
type LocationForm = z.infer<typeof locationSchema>
const EMPTY_LOCATIONS: CaseLocation[] = []

export function MapPanel({caseId, readOnly = false}: { caseId: string; readOnly?: boolean }) {
    const [creating, setCreating] = useState(false)
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [search, setSearch] = useState('')
    const [evidenceIds, setEvidenceIds] = useState<string[]>([])
    const [personIds, setPersonIds] = useState<string[]>([])
    const query = useQuery({queryKey: ['case', caseId, 'locations'], queryFn: () => api.locations(caseId)})
    const locations = query.data ?? EMPTY_LOCATIONS
    const visible = useMemo(() => {
        const term = search.trim().toLowerCase();
        return locations.filter((item) => !term || `${item.name} ${item.description} ${item.location_type}`.toLowerCase().includes(term))
    }, [locations, search])
    const selected = locations.find((item) => item.id === selectedId) ?? visible[0] ?? null
    const form = useForm<LocationForm>({
        resolver: zodResolver(locationSchema),
        defaultValues: {
            location_type: 'event',
            occurred_on: '',
            precision: 'approximate',
            verification_status: 'unverified',
            source_url: ''
        }
    })
    const refresh = () => queryClient.invalidateQueries({queryKey: ['case', caseId, 'locations']})
    const create = useMutation({
        mutationFn: (data: LocationForm) => api.createLocation(caseId, {
            ...data,
            occurred_on: data.occurred_on || null,
            source_url: data.source_url || undefined,
            evidence_ids: evidenceIds,
            person_ids: personIds
        }), onSuccess: async (location) => {
            form.reset({
                location_type: 'event',
                occurred_on: '',
                precision: 'approximate',
                verification_status: 'unverified',
                source_url: '',
                name: '',
                description: '',
                latitude: 0,
                longitude: 0
            });
            setEvidenceIds([]);
            setPersonIds([]);
            setCreating(false);
            setSelectedId(location.id);
            await refresh()
        }
    })
    const review = useMutation({
        mutationFn: ({id, status}: {
            id: string;
            status: 'confirmed' | 'rejected'
        }) => api.reviewLocation(caseId, id, status), onSuccess: async (_, variables) => {
            if (variables.status === 'rejected') setSelectedId(null);
            await refresh()
        }
    })

    if (query.isLoading) return <div className="card grid min-h-[460px] place-items-center">
        <div className="text-center"><Sparkles className="mx-auto animate-pulse text-accent"/><p
            className="mt-3 text-xs text-muted">Loading case locations…</p></div>
    </div>
    if (query.isError) return <div className="error-banner"><p>Case locations could not be loaded.</p>
        <button type="button" onClick={() => query.refetch()} className="secondary-button mt-3 text-xs">Try again
        </button>
    </div>

    return <section>
        <header className="flex flex-col gap-4 border-b border-subtle pb-5 sm:flex-row sm:items-end sm:justify-between">
            <div><p className="eyebrow">Geographic record</p><h2 className="page-title mt-2">Case Locations</h2><p
                className="mt-2 text-[15px] text-secondary">Select a location to inspect where it sits in the case.</p>
            </div>
            {readOnly ? <UpgradeButton description="Adding and reviewing case locations is available on the Investigator plan.">Add location</UpgradeButton> : <button type="button" onClick={() => setCreating((value) => !value)}
                    className="primary-button shrink-0 text-xs"><Plus size={15}/>{creating ? 'Close' : 'Add location'}
            </button>}
        </header>

        {creating &&
            <LocationFormView caseId={caseId} form={form} onSubmit={form.handleSubmit((data) => create.mutate(data))}
                              pending={create.isPending} error={create.error} evidenceIds={evidenceIds}
                              personIds={personIds}
                              toggleEvidence={(id) => setEvidenceIds((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id])}
                              togglePerson={(id) => setPersonIds((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id])}/>}

        {!locations.length && !creating ?
            <div className="card mt-5 grid min-h-[400px] place-items-center p-8 text-center">
                <div><MapPinned size={34} className="mx-auto text-muted"/><h3 className="empty-title mt-4">No locations
                    mapped yet</h3><p className="mx-auto mt-2 max-w-md font-display text-lg text-secondary">A case
                    becomes easier to understand when its events have a place.</p><p
                    className="mt-3 text-xs text-muted">Add the first location, or rerun AI research to extract sourced
                    public locations.</p></div>
            </div> : locations.length > 0 && <div className="mt-5 grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
            <aside className="order-2 lg:order-1"><label className="relative block"><Search size={15}
                                                                                            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted"/><input
                value={search} onChange={(event) => setSearch(event.target.value)} className="field pl-9"
                placeholder="Search locations…"/><span className="sr-only">Search locations</span></label>
                <div className="mt-3 max-h-[560px] space-y-2 overflow-y-auto pr-1">{visible.map((location) =>
                    <LocationRow key={location.id} location={location} selected={location.id === selected?.id}
                                 onSelect={() => setSelectedId(location.id)}/>)}{!visible.length &&
                    <div className="card p-6 text-center text-xs text-muted">No locations match this
                        search.</div>}</div>
            </aside>
            <main className="order-1 lg:order-2">{selected &&
                <MapView location={selected} review={review.mutate} readOnly={readOnly}/>}</main>
        </div>}
    </section>
}

function LocationRow({location, selected, onSelect}: {
    location: CaseLocation;
    selected: boolean;
    onSelect: () => void
}) {
    const config = typeConfig[location.location_type]
    return <button type="button" onClick={onSelect}
                   className={`block w-full rounded-xl border p-4 text-left transition duration-200 ${selected ? 'border-accent/50 bg-accent-muted shadow-card' : 'border-subtle bg-surface/85 hover:border-default hover:bg-elevated/80'}`}>
        <div className="flex items-start gap-3"><span
            className={`mt-1.5 size-2.5 shrink-0 rounded-full ${config.color}`}/><span className="min-w-0 flex-1"><span
            className="block text-sm font-semibold text-primary">{location.name}</span><span
            className="mt-1 block text-[10px] font-semibold uppercase tracking-[.08em] text-muted">{config.label}{location.occurred_on ? ` · ${formatDate(location.occurred_on)}` : ''}</span><span
            className="mt-2 line-clamp-2 block text-xs leading-5 text-secondary">{location.description}</span></span>{location.ai_suggested && location.review_status === 'suggested' &&
            <span className="ai-label shrink-0">AI</span>}</div>
    </button>
}

function MapView({location, review, readOnly}: {
    location: CaseLocation;
    review: (value: { id: string; status: 'confirmed' | 'rejected' }) => void;
    readOnly: boolean
}) {
    const hasCoordinates = location.latitude !== null && location.longitude !== null
    const mapQuery = hasCoordinates ? `${location.latitude},${location.longitude}` : location.name
    const coordinateLabel = hasCoordinates ? `${location.latitude!.toFixed(4)}, ${location.longitude!.toFixed(4)}` : null
    const mapUrl = `https://www.google.com/maps?q=${encodeURIComponent(mapQuery)}&z=${location.precision === 'exact' && hasCoordinates ? 15 : 12}&output=embed`
    const openUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(mapQuery)}`
    return <div className="overflow-hidden rounded-xl border border-subtle bg-surface shadow-card">
        <div className="relative h-[360px] bg-tertiary sm:h-[470px]">
            <iframe key={`${location.id}-${mapQuery}`} title={`Map showing ${location.name}`} src={mapUrl}
                    loading="lazy" referrerPolicy="no-referrer-when-downgrade"
                    className="absolute inset-0 size-full border-0"
                    style={{filter: 'grayscale(.35) brightness(.72) contrast(1.12)'}}/>
            <span
                className="pointer-events-none absolute left-4 top-4 rounded-md border border-accent/40 bg-background/90 px-3 py-2 text-[10px] font-semibold text-accent shadow-card"><LocateFixed
                size={13}
                className="mr-1.5 inline"/>{hasCoordinates ? (location.precision === 'exact' ? 'Exact public location' : 'Approximate location') : 'Located by public place name'}</span>
        </div>
        <div className="p-5">
            <div className="flex items-start justify-between gap-4">
                <div><p className="eyebrow">{typeConfig[location.location_type].label}</p><h3
                    className="section-title mt-2">{location.name}</h3></div>
                <a href={openUrl} target="_blank" rel="noreferrer"
                   className="secondary-button min-h-10 shrink-0 px-3 text-[10px]"><ExternalLink size={13}/>Open map</a>
            </div>
            <p className="mt-3 text-sm leading-6 text-secondary">{location.description}</p>
            <div className="mt-4 flex flex-wrap gap-2"><span
                className="status-badge">{location.verification_status.replaceAll('_', ' ')}</span>{location.occurred_on &&
                <span className="status-badge">{formatDate(location.occurred_on)}</span>}{coordinateLabel &&
                <span className="status-badge">{coordinateLabel}</span>}{!hasCoordinates &&
                <span className="status-badge">Place-name lookup</span>}</div>
            <LinkedPeople people={location.people}/>{location.evidence.length > 0 &&
            <div className="mt-4 grid gap-2 sm:grid-cols-2">{location.evidence.map((item) => <EvidenceCard key={item.id}
                                                                                                           caseId={location.case_id}
                                                                                                           item={item}
                                                                                                           compact/>)}</div>}{location.source_url &&
            <a href={location.source_url} target="_blank" rel="noreferrer"
               className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-blue"><ExternalLink
                size={13}/>{location.source_title || 'Inspect supporting source'}
            </a>}{location.ai_suggested && location.review_status === 'suggested' &&
            <div className="mt-4 flex items-center justify-between gap-3 border-t border-subtle pt-4"><p
                className="text-[10px] text-muted">AI suggested from public research. Review before treating as
                canonical.</p>
                {!readOnly && <div className="flex">
                    <button type="button" onClick={() => review({id: location.id, status: 'confirmed'})}
                            className="ghost-button min-h-9 px-2 text-[10px] text-success"><Check size={13}/>Confirm
                    </button>
                    <button type="button" onClick={() => review({id: location.id, status: 'rejected'})}
                            className="ghost-button min-h-9 px-2 text-[10px] text-danger"><X size={13}/>Reject
                    </button>
                </div>}
            </div>}</div>
    </div>
}

function LocationFormView({
                              caseId,
                              form,
                              onSubmit,
                              pending,
                              error,
                              evidenceIds,
                              personIds,
                              toggleEvidence,
                              togglePerson
                          }: {
    caseId: string;
    form: ReturnType<typeof useForm<LocationForm>>;
    onSubmit: () => void;
    pending: boolean;
    error: Error | null;
    evidenceIds: string[];
    personIds: string[];
    toggleEvidence: (id: string) => void;
    togglePerson: (id: string) => void
}) {
    const fieldError = (name: keyof LocationForm) => form.formState.errors[name]?.message
    return <form onSubmit={onSubmit} className="card mt-5 border-default p-5 sm:p-6">
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Location name" error={fieldError('name')}><input
            className="field mt-2" placeholder="North trailhead" {...form.register('name')}/></Field><Field
            label="Location type" error={fieldError('location_type')}><select
            className="field mt-2" {...form.register('location_type')}>{locationTypes.map((item) => <option
            key={item.value} value={item.value}>{item.label}</option>)}</select></Field><Field label="Latitude"
                                                                                               error={fieldError('latitude')}><input
            type="number" step="any" className="field mt-2"
            placeholder="45.5152" {...form.register('latitude', {valueAsNumber: true})}/></Field><Field
            label="Longitude" error={fieldError('longitude')}><input type="number" step="any" className="field mt-2"
                                                                     placeholder="-122.6784" {...form.register('longitude', {valueAsNumber: true})}/></Field><Field
            label="Date (optional)" error={fieldError('occurred_on')}><input type="date"
                                                                             className="field mt-2 [color-scheme:dark]" {...form.register('occurred_on')}/></Field><Field
            label="Coordinate precision" error={fieldError('precision')}><select
            className="field mt-2" {...form.register('precision')}>
            <option value="approximate">Approximate</option>
            <option value="exact">Exact public location</option>
        </select></Field><Field label="Verification" error={fieldError('verification_status')}><select
            className="field mt-2" {...form.register('verification_status')}>
            <option value="unverified">Unverified</option>
            <option value="source_backed">Source-backed</option>
            <option value="verified">Verified</option>
            <option value="disputed">Disputed</option>
        </select></Field><Field label="Public source URL (optional)" error={fieldError('source_url')}><input type="url"
                                                                                                             className="field mt-2"
                                                                                                             placeholder="https://…" {...form.register('source_url')}/></Field>
        </div>
        <Field label="Why this location matters" error={fieldError('description')}><textarea
            className="field mt-2 min-h-28 resize-y py-3"
            placeholder="Explain how this public location relates to the case and where the information came from." {...form.register('description')}/></Field>
        <div className="mt-4 grid gap-3 md:grid-cols-2"><EvidencePicker caseId={caseId} selected={evidenceIds}
                                                                        onToggle={toggleEvidence}/><PersonPicker
            caseId={caseId} selected={personIds} onToggle={togglePerson}/></div>
        <p className="metadata mt-3 text-[10px]">Use decimal coordinates. In Google Maps, right-click a public point to
            copy its coordinates. Do not enter a private home address.</p>{error && <p role="alert"
                                                                                       className="error-banner mt-4">{error instanceof ApiError ? error.message : 'The location could not be saved'}</p>}
        <button disabled={pending} className="primary-button mt-4 text-xs"><MapPinned
            size={15}/>{pending ? 'Saving…' : 'Add location'}</button>
    </form>
}

function Field({label, error, children}: { label: string; error?: string; children: ReactNode }) {
    return <label className="block text-xs font-semibold text-primary">{label}{children}{error &&
        <span className="mt-1 block text-xs text-danger">{error}</span>}</label>
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeZone: 'UTC'
    }).format(new Date(`${value}T00:00:00Z`))
}
