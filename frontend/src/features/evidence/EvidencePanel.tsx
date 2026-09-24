import {useInfiniteQuery, useMutation} from '@tanstack/react-query'
import {ChevronDown, FileUp, Link2, Plus, ShieldCheck} from 'lucide-react'
import {useState} from 'react'
import {queryClient} from '../../lib/query'
import {ApiError, api} from '../../services/api'
import {EvidenceCard} from './EvidenceCard'
import {UpgradeButton} from '../../components/ui/Visual'

export function EvidencePanel({caseId, readOnly = false, canComment = false}: { caseId: string; readOnly?: boolean; canComment?: boolean }) {
    const [mode, setMode] = useState<'file' | 'link' | null>(null)
    const query = useInfiniteQuery({
        queryKey: ['case', caseId, 'evidence'],
        queryFn: ({pageParam}) => api.evidence(caseId, pageParam),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    })
    const items = query.data?.pages.flatMap((page) => page.items) ?? []
    const total = query.data?.pages[0]?.total ?? 0
    const refresh = () => queryClient.invalidateQueries({queryKey: ['case', caseId, 'evidence']})
    return <section className="min-w-0 max-w-full overflow-x-hidden">
        <div className="flex flex-wrap items-end justify-between gap-4">
            <div><p className="eyebrow">Case record</p><h2 className="section-title mt-2">Evidence library{total > 0 && <span className="ml-2 font-ui text-xs font-medium text-muted">{total}</span>}</h2><p
                className="mt-2 max-w-xl text-[15px] leading-6 text-secondary">Upload original files or preserve a
                reference to a public webpage or video. Items stay reusable across the case.</p></div>
            {!readOnly ? <div className="flex gap-2">
                <button onClick={() => setMode(mode === 'file' ? null : 'file')} className="primary-button text-xs">
                    <FileUp size={15}/> Upload
                </button>
                <button onClick={() => setMode(mode === 'link' ? null : 'link')} className="secondary-button text-xs">
                    <Plus size={15}/> Add link
                </button>
            </div> : <UpgradeButton description="Uploading files and adding evidence links are available on the Investigator plan.">Add evidence</UpgradeButton>}
        </div>
        {mode === 'file' && <UploadForm caseId={caseId} done={async () => {
            setMode(null);
            await refresh()
        }}/>} {mode === 'link' && <LinkForm caseId={caseId} done={async () => {
        setMode(null);
        await refresh()
    }}/>}
        <div className="mt-5 grid min-w-0 max-w-full gap-3 md:grid-cols-2">{items.map((item) => <EvidenceCard key={item.id}
                                                                                                  caseId={caseId}
                                                                                                  item={item}
                                                                                                  canComment={canComment}/>)}</div>
        {query.hasNextPage && <div className="mt-5 flex justify-center"><button type="button" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage} className="secondary-button text-xs"><ChevronDown size={15}/>{query.isFetchingNextPage ? 'Loading evidence…' : 'Load more evidence'}</button></div>}
        {!query.isLoading && !items.length && !mode &&
            <div className="card mt-5 grid min-h-56 place-items-center p-8 text-center">
                <div><ShieldCheck className="mx-auto text-muted"/><h3 className="empty-title mt-4">No evidence yet</h3>
                    <p className="mt-2 font-display text-lg text-secondary">Every case starts with an unanswered
                        question.</p><p className="mt-2 text-sm text-muted">Upload a document or add a public source
                        link.</p></div>
            </div>}
    </section>
}

function UploadForm({caseId, done}: { caseId: string; done: () => Promise<void> }) {
    const [error, setError] = useState('')
    const mutation = useMutation({
        mutationFn: async (form: FormData) => {
            const file = form.get('file') as File;
            if (!file?.size) throw new Error('Choose a file');
            const ticket = await api.requestEvidenceUpload(caseId, {
                title: String(form.get('title')),
                description: String(form.get('description') || '') || undefined,
                filename: file.name,
                content_type: file.type || 'application/octet-stream',
                file_size: file.size
            });
            const response = await fetch(ticket.upload_url, {
                method: ticket.upload_method,
                headers: ticket.upload_headers,
                body: file
            });
            if (!response.ok) throw new Error('Storage rejected the upload');
            return api.completeEvidenceUpload(caseId, ticket.evidence.id)
        },
        onSuccess: done,
        onError: (value) => setError(value instanceof ApiError || value instanceof Error ? value.message : 'Upload failed')
    })
    return <form className="card mt-5 p-5" onSubmit={(event) => {
        event.preventDefault();
        setError('');
        mutation.mutate(new FormData(event.currentTarget))
    }}><p className="flex items-center gap-2 text-sm font-semibold text-primary"><FileUp size={17}
                                                                                         className="text-accent"/> Upload
        a file</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field name="title" label="Evidence title" required/><label
            className="text-xs font-semibold text-primary">File<input name="file" type="file" required
                                                                      accept=".pdf,.txt,.csv,.docx,.png,.jpg,.jpeg,.webp,.mp3,.wav,.mp4"
                                                                      className="field mt-2 file:mr-3 file:rounded-md file:border-0 file:bg-accent file:px-3 file:py-1 file:text-xs file:font-semibold file:text-background"/></label>
        </div>
        <Field name="description" label="Description (optional)"/><ErrorText value={error}/>
        <button disabled={mutation.isPending}
                className="primary-button mt-4 text-xs">{mutation.isPending ? 'Validating upload…' : 'Upload evidence'}</button>
        <p className="metadata mt-3 text-[10px]">PDF, Office document, text, image, audio, or MP4 · 25 MB maximum</p>
    </form>
}

function LinkForm({caseId, done}: { caseId: string; done: () => Promise<void> }) {
    const [error, setError] = useState('')
    const mutation = useMutation({
        mutationFn: (form: FormData) => {
            const url = String(form.get('url'));
            const youtube = /(?:youtube\.com|youtu\.be)/i.test(url);
            return api.createEvidenceLink(caseId, {
                title: String(form.get('title')),
                description: String(form.get('description') || '') || undefined,
                url,
                evidence_type: youtube ? 'video' : 'article'
            })
        },
        onSuccess: done,
        onError: (value) => setError(value instanceof ApiError || value instanceof Error ? value.message : 'Link could not be saved')
    })
    return <form className="card mt-5 p-5" onSubmit={(event) => {
        event.preventDefault();
        setError('');
        mutation.mutate(new FormData(event.currentTarget))
    }}><p className="flex items-center gap-2 text-sm font-semibold text-primary"><Link2 size={17}
                                                                                        className="text-accent"/> Add a
        public link</p>
        <div className="mt-4 grid gap-4 sm:grid-cols-2"><Field name="title" label="Evidence title" required/><Field
            name="url" label="YouTube or website URL" type="url" required/></div>
        <Field name="description" label="Why this matters (optional)"/><ErrorText value={error}/>
        <button disabled={mutation.isPending}
                className="primary-button mt-4 text-xs">{mutation.isPending ? 'Saving…' : 'Save link'}</button>
    </form>
}

function Field({name, label, type = 'text', required = false}: {
    name: string;
    label: string;
    type?: string;
    required?: boolean
}) {
    return <label className="mt-4 block text-xs font-semibold text-primary first:mt-0">{label}<input name={name}
                                                                                                     type={type}
                                                                                                     required={required}
                                                                                                     className="field mt-2"/></label>
}

function ErrorText({value}: { value: string }) {
    return value ? <p role="alert" className="mt-3 text-xs text-danger">{value}</p> : null
}
