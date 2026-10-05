import {useEffect, useState, type ReactNode} from 'react'
import {CheckCircle2, ExternalLink, Film, Save, Sparkles} from 'lucide-react'
import {useMutation, useQuery} from '@tanstack/react-query'
import {api, ApiError} from '../../services/api'
import {queryClient} from '../../lib/query'
import type {ReelDraft, ReelDraftInput} from '../../types'

export function ReelsPanel({caseId}: {caseId: string}) {
    const query = useQuery({queryKey: ['case', caseId, 'reels'], queryFn: () => api.reels(caseId)})
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const selected = query.data?.find((item) => item.id === selectedId) ?? query.data?.[0]

    useEffect(() => {
        if (!selectedId && query.data?.[0]) setSelectedId(query.data[0].id)
    }, [query.data, selectedId])

    if (query.isLoading) return <div className="card h-56 animate-pulse"/>
    if (query.error) return <p role="alert" className="error-banner">Reel drafts could not be loaded.</p>
    if (!query.data?.length) return <section className="card grid min-h-72 place-items-center p-8 text-center"><div><Film className="mx-auto text-muted"/><h2 className="empty-title mt-4">No reel drafts yet</h2><p className="mt-2 max-w-md text-sm leading-6 text-muted">Ask the Researcher to “create a reel” about a sourced part of this case. The script and scene plan will appear here for review.</p></div></section>

    return <div className="grid gap-5 lg:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="card h-fit p-3"><p className="eyebrow px-2 py-2">Reel drafts</p><div className="space-y-1">{query.data.map((item) => <button key={item.id} type="button" onClick={() => setSelectedId(item.id)} className={`w-full rounded-lg p-3 text-left transition ${selected?.id === item.id ? 'bg-accent-muted text-primary' : 'text-secondary hover:bg-tertiary'}`}><span className="block text-xs font-semibold">{item.title}</span><span className="metadata mt-1 block text-[9px]">{item.duration_seconds}s · {item.status}{item.automated ? ' · scheduled' : ''}</span></button>)}</div></aside>
        {selected && <ReelEditor key={selected.id} caseId={caseId} item={selected} />}
    </div>
}

function ReelEditor({caseId, item}: {caseId: string; item: ReelDraft}) {
    const [draft, setDraft] = useState<ReelDraftInput>({title: item.title, hook: item.hook, narration: item.narration, caption: item.caption, duration_seconds: item.duration_seconds, scenes: item.scenes, sources: item.sources})
    const [status, setStatus] = useState(item.status)
    const mutation = useMutation({
        mutationFn: (nextStatus: 'draft' | 'approved') => api.updateReel(caseId, item.id, {...draft, status: nextStatus}),
        onSuccess: async (saved) => {
            setStatus(saved.status)
            await queryClient.invalidateQueries({queryKey: ['case', caseId, 'reels']})
        },
    })
    return <section className="card overflow-hidden">
        <div className="border-b border-subtle p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="eyebrow">9:16 reel preview</p><h2 className="section-title mt-2">{draft.title}</h2></div><span className={status === 'approved' || status === 'published' ? 'ai-label' : 'metadata'}>{status === 'approved' || status === 'published' ? <><CheckCircle2 size={12}/> {status === 'published' ? 'Published' : 'Approved'}</> : status.replaceAll('_', ' ')}</span></div>{item.youtube_url && <a href={item.youtube_url} target="_blank" rel="noreferrer" className="mt-3 inline-flex items-center gap-1 text-xs text-blue">Watch on YouTube <ExternalLink size={11}/></a>}{item.error_message && <p role="alert" className="error-banner mt-3">{item.error_message}</p>}</div>
        <div className="grid gap-6 p-5 sm:p-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
            <div className="space-y-5">
                <Field label="Title"><input className="field" disabled={item.automated} maxLength={100} value={draft.title} onChange={(event) => setDraft({...draft, title: event.target.value})}/></Field>
                <Field label="Opening hook"><textarea className="field min-h-20" disabled={item.automated} maxLength={280} value={draft.hook} onChange={(event) => setDraft({...draft, hook: event.target.value})}/></Field>
                <Field label="Narration"><textarea className="field min-h-48" disabled={item.automated} maxLength={5000} value={draft.narration} onChange={(event) => setDraft({...draft, narration: event.target.value})}/></Field>
                <Field label="Post caption"><textarea className="field min-h-32" disabled={item.automated} maxLength={2200} value={draft.caption} onChange={(event) => setDraft({...draft, caption: event.target.value})}/></Field>
                <div><p className="eyebrow">Scene plan</p><div className="mt-3 space-y-3">{draft.scenes.map((scene, index) => <article key={`${scene.start_second}-${index}`} className="rounded-lg border border-subtle bg-tertiary/50 p-4"><p className="text-[10px] font-semibold uppercase tracking-wider text-accent">{scene.start_second}s–{scene.end_second}s</p><label className="mt-3 block text-[10px] uppercase tracking-wider text-muted">On-screen text<input className="field mt-1" disabled={item.automated} maxLength={180} value={scene.on_screen_text} onChange={(event) => setDraft({...draft, scenes: draft.scenes.map((value, sceneIndex) => sceneIndex === index ? {...value, on_screen_text: event.target.value} : value)})}/></label><label className="mt-3 block text-[10px] uppercase tracking-wider text-muted">Visual direction<textarea className="field mt-1 min-h-20" disabled={item.automated} maxLength={500} value={scene.visual_direction} onChange={(event) => setDraft({...draft, scenes: draft.scenes.map((value, sceneIndex) => sceneIndex === index ? {...value, visual_direction: event.target.value} : value)})}/></label></article>)}</div></div>
                <div><p className="eyebrow">Sources</p><ul className="mt-3 space-y-2">{draft.sources.map((source) => <li key={source.url}><a href={source.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-blue hover:text-primary">{source.title}<ExternalLink size={11}/></a></li>)}</ul></div>
            </div>
            <aside className="mx-auto w-full max-w-[18rem]"><div className="aspect-[9/16] overflow-hidden rounded-[1.5rem] border border-white/15 bg-[radial-gradient(circle_at_50%_20%,rgba(213,166,74,.24),transparent_35%),linear-gradient(160deg,#17212a,#070a0e)] p-5 shadow-2xl"><div className="flex h-full flex-col"><span className="ai-label w-fit"><Sparkles size={11}/> Draft</span><div className="my-auto"><p className="font-display text-2xl leading-tight text-primary">{draft.hook}</p><p className="mt-4 text-[11px] leading-5 text-secondary">{draft.scenes[0]?.on_screen_text}</p></div><p className="text-[9px] uppercase tracking-[.18em] text-accent">Case Theory · {draft.duration_seconds}s</p></div></div><p className="mt-3 text-center text-[10px] text-muted">Storyboard preview. Rendering comes next.</p></aside>
        </div>
        {!item.automated && <div className="flex flex-wrap items-center justify-between gap-3 border-t border-subtle p-5 sm:px-6"><div>{mutation.error && <p role="alert" className="text-xs text-danger">{mutation.error instanceof ApiError ? mutation.error.message : 'The reel draft could not be saved.'}</p>}</div><div className="flex gap-2"><button type="button" onClick={() => mutation.mutate('draft')} disabled={mutation.isPending} className="secondary-button w-fit text-xs"><Save size={14}/>Save draft</button><button type="button" onClick={() => mutation.mutate('approved')} disabled={mutation.isPending} className="primary-button w-fit px-4 text-xs"><CheckCircle2 size={14}/>{mutation.isPending ? 'Saving…' : 'Approve script'}</button></div></div>}
    </section>
}

function Field({label, children}: {label: string; children: ReactNode}) {
    return <label className="block"><span className="eyebrow">{label}</span><span className="mt-2 block">{children}</span></label>
}
