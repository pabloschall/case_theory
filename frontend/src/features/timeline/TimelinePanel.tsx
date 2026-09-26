import {zodResolver} from '@hookform/resolvers/zod'
import {useMutation} from '@tanstack/react-query'
import {CalendarPlus, ExternalLink, Plus} from 'lucide-react'
import {useState} from 'react'
import {useForm} from 'react-hook-form'
import {Link} from 'react-router'
import {z} from 'zod'
import {queryClient} from '../../lib/query'
import {ApiError, api} from '../../services/api'
import type {CaseDetail} from '../../types'
import {EvidenceCard} from '../evidence/EvidenceCard'
import {EvidencePicker} from '../evidence/EvidencePicker'
import {LinkedPeople, PersonPicker} from '../people/PersonPicker'

const eventSchema = z.object({
    occurred_on: z.iso.date('Choose a valid date'),
    occurred_time: z.union([z.literal(''), z.string().regex(/^([01]\d|2[0-3]):[0-5]\d$/, 'Choose a valid time')]).optional(),
    title: z.string().trim().min(2, 'Add a short event title').max(240),
    description: z.string().trim().min(1, 'Describe what happened').max(5000),
})
type EventForm = z.infer<typeof eventSchema>

export function TimelinePanel({item, readOnly = false}: { item: CaseDetail; readOnly?: boolean }) {
    const [creating, setCreating] = useState(false)
    const [attaching, setAttaching] = useState<string | null>(null)
    const [selected, setSelected] = useState<string[]>([])
    const [personIds, setPersonIds] = useState<string[]>([])
    const form = useForm<EventForm>({resolver: zodResolver(eventSchema)})
    const refresh = () => queryClient.invalidateQueries({queryKey: ['case', item.id]})
    const create = useMutation({
        mutationFn: (data: EventForm) => api.createTimelineEvent(item.id, {
            ...data,
            occurred_time: data.occurred_time || null,
            evidence_ids: selected,
            person_ids: personIds
        }),
        onSuccess: async () => {
            form.reset();
            setSelected([]);
            setPersonIds([]);
            setCreating(false);
            await refresh()
        },
    })
    const attach = useMutation({
        mutationFn: ({eventId, evidenceId}: {
            eventId: string;
            evidenceId: string
        }) => api.attachTimelineEvidence(item.id, eventId, evidenceId),
        onSuccess: async () => {
            setAttaching(null);
            setSelected([]);
            await refresh()
        },
    })

    return <section className="card p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
            <div><p className="eyebrow">Case chronology</p><h2 className="section-title mt-2">Timeline</h2></div>
            {readOnly ? <Link to="/login" className="secondary-button text-xs">Sign in to add event</Link> : <button type="button" onClick={() => {
                setCreating((value) => !value);
                setSelected([]);
                setPersonIds([])
            }} className="primary-button text-xs"><CalendarPlus size={16}/>{creating ? 'Close' : 'Add event'}</button>}
        </div>
        {creating && <form onSubmit={form.handleSubmit((data) => create.mutate(data))}
                           className="mt-5 rounded-xl border border-subtle bg-background/35 p-5">
            <div className="grid gap-4 md:grid-cols-[180px_150px_1fr]"><label className="text-xs font-semibold text-primary">Event
                date<input type="date"
                           className="field mt-2 [color-scheme:dark]" {...form.register('occurred_on')}/><FieldError
                    value={form.formState.errors.occurred_on?.message}/></label><label className="text-xs font-semibold text-primary">Event time <span className="font-normal text-muted">(optional)</span><input type="time"
                           className="field mt-2 [color-scheme:dark]" {...form.register('occurred_time')}/><FieldError
                    value={form.formState.errors.occurred_time?.message}/></label><label
                className="text-xs font-semibold text-primary">Event title<input className="field mt-2"
                                                                                 placeholder="Vehicle recorded near trailhead" {...form.register('title')}/><FieldError
                value={form.formState.errors.title?.message}/></label></div>
            <label className="mt-4 block text-xs font-semibold text-primary">Description<textarea
                className="field mt-2 min-h-28 resize-y py-3"
                placeholder="State what is known and avoid presenting theories as facts." {...form.register('description')}/><FieldError
                value={form.formState.errors.description?.message}/></label>
            <div className="mt-4 grid gap-3 md:grid-cols-2"><EvidencePicker caseId={item.id} selected={selected}
                                                                            onToggle={(id) => setSelected((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id])}/><PersonPicker
                caseId={item.id} selected={personIds}
                onToggle={(id) => setPersonIds((ids) => ids.includes(id) ? ids.filter((value) => value !== id) : [...ids, id])}/>
            </div>
            {create.error && <p role="alert"
                                className="mt-3 text-xs text-danger">{create.error instanceof ApiError ? create.error.message : 'The timeline event could not be saved'}</p>}
            <button disabled={create.isPending} className="primary-button mt-4 text-xs"><Plus
                size={15}/>{create.isPending ? 'Adding event…' : 'Add to timeline'}</button>
            <p className="metadata mt-3 text-[10px]">User-added events begin as unverified and remain separate from
                AI-generated suggestions.</p></form>}
        {item.timeline.length ? <div className="mt-6 space-y-0">{item.timeline.map((event) => <article key={event.id}
                                                                                                       className="relative border-l border-accent/25 pb-7 pl-7 last:pb-0">
            <span
                className={`absolute -left-[5px] top-1 size-[10px] rounded-full border border-surface ${event.verification_status === 'verified' ? 'bg-success' : event.verification_status === 'disputed' ? 'bg-danger' : event.ai_generated ? 'bg-accent' : 'bg-warning'}`}/>
            <div className="flex flex-wrap items-center gap-2"><p
                className="metadata text-[10px] uppercase tracking-[.1em]">{event.date_label} · {event.verification_status.replaceAll('_', ' ')}</p>
                <span
                    className={event.ai_generated ? 'ai-label' : 'status-badge'}>{event.ai_generated ? 'AI suggested' : 'User added'}</span>
            </div>
            <h3 className="mt-2 text-base font-semibold text-primary">{event.title}</h3><p
            className="mt-2 text-sm leading-6 text-secondary">{event.description}</p><LinkedPeople
            people={event.people}/>
            <div className="mt-3 flex flex-wrap gap-2">{event.sources.map((source) => <a key={source.id}
                                                                                         href={source.url}
                                                                                         target="_blank"
                                                                                         rel="noreferrer"
                                                                                         className="inline-flex items-center gap-1 rounded-md border border-info/30 px-2.5 py-1 text-[10px] text-blue hover:border-info/50"><ExternalLink
                size={11}/>{source.publisher || source.title}</a>)}</div>
            {event.evidence.length > 0 &&
                <div className="mt-3 grid gap-2 sm:grid-cols-2">{event.evidence.map((evidence) => <EvidenceCard
                    key={evidence.id} caseId={item.id} item={evidence} compact/>)}</div>}
            {!readOnly && <><button type="button" onClick={() => {
                setAttaching(attaching === event.id ? null : event.id);
                setSelected([])
            }}
                    className="ghost-button mt-2 px-0 text-[10px] font-semibold uppercase tracking-[.1em] text-accent">{attaching === event.id ? 'Cancel' : '+ Attach evidence'}</button>
            {attaching === event.id && <div className="mt-2"><EvidencePicker caseId={item.id} selected={selected}
                                                                             onToggle={(id) => setSelected([id])}/>
                <button type="button" disabled={!selected[0] || attach.isPending}
                        onClick={() => attach.mutate({eventId: event.id, evidenceId: selected[0]})}
                        className="primary-button mt-2 min-h-10 text-xs">Link to event
                </button>
            </div>}</>}</article>)}</div> : !creating &&
            <div className="mt-8 py-12 text-center"><CalendarPlus className="mx-auto text-muted"/><h3
                className="empty-title mt-4">No timeline events yet</h3><p className="mt-2 text-sm text-muted">Add the
                first known event.</p></div>}
    </section>
}

function FieldError({value}: { value?: string }) {
    return value ? <span className="mt-1 block text-xs text-danger">{value}</span> : null
}
