import {zodResolver} from '@hookform/resolvers/zod'
import {useInfiniteQuery, useMutation} from '@tanstack/react-query'
import {ArrowLeft, ChevronDown, ChevronRight, ChevronUp, Clock3, FileText, MessageCircle, Plus, Send, Sparkles} from 'lucide-react'
import {useState, type ReactNode} from 'react'
import {useForm} from 'react-hook-form'
import {Link} from 'react-router'
import {z} from 'zod'
import {queryClient} from '../../lib/query'
import {ApiError, api} from '../../services/api'
import type {DiscussionComment, DiscussionThread} from '../../types'
import {EvidenceCard} from '../evidence/EvidenceCard'
import {EvidencePicker} from '../evidence/EvidencePicker'
import {LinkedPeople, PersonPicker} from '../people/PersonPicker'
import {ReportButton} from '../moderation/ReportButton'

const threadTypes = {
    question: {
        label: 'Open question',
        edge: 'border-l-blue',
        badge: 'border-blue/30 bg-blue-muted text-blue',
        glow: 'hover:shadow-[0_8px_28px_rgba(106,155,196,.10)]'
    },
    theory: {
        label: 'Theory',
        edge: 'border-l-warning',
        badge: 'border-warning/30 bg-warning/10 text-warning',
        glow: 'hover:shadow-[0_8px_28px_rgba(215,162,76,.10)]'
    },
    evidence: {
        label: 'Evidence-backed',
        edge: 'border-l-teal',
        badge: 'border-teal/30 bg-teal-muted text-teal',
        glow: 'hover:shadow-[0_8px_28px_rgba(103,168,154,.10)]'
    },
    dispute: {
        label: 'Disputed',
        edge: 'border-l-rust',
        badge: 'border-rust/30 bg-rust-muted text-rust',
        glow: 'hover:shadow-[0_8px_28px_rgba(184,107,86,.12)]'
    },
} as const

const threadSchema = z.object({
    thread_type: z.enum(['question', 'theory', 'evidence', 'dispute']),
    title: z.string().trim().min(3, 'Add a short title').max(140),
    body: z.string().trim().max(5000),
    ai_search: z.boolean(),
}).refine((data) => data.ai_search || data.body.length > 0, {
    message: 'Add the opening text',
    path: ['body'],
})
const commentSchema = z.object({body: z.string().trim().min(1, 'Add a comment').max(3000)})
type ThreadForm = z.infer<typeof threadSchema>
type CommentForm = z.infer<typeof commentSchema>
const reactionOptions = ['👍', '❤️', '🤔', '🔎', '❓'] as const

export function DiscussionPanel({caseId, readOnly = false}: { caseId: string; readOnly?: boolean }) {
    const [creating, setCreating] = useState(false)
    const [selectedId, setSelectedId] = useState<string | null>(null)
    const [evidenceIds, setEvidenceIds] = useState<string[]>([])
    const [personIds, setPersonIds] = useState<string[]>([])
    const query = useInfiniteQuery({
        queryKey: ['case', caseId, 'discussions'],
        queryFn: ({pageParam}) => api.discussionThreads(caseId, pageParam),
        initialPageParam: undefined as string | undefined,
        getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    })
    const threads = query.data?.pages.flatMap((page) => page.items) ?? []
    const discussionStats = query.data?.pages[0]
    const totalThreads = discussionStats?.total ?? 0
    const selected = threads.find((thread) => thread.id === selectedId)
    const threadForm = useForm<ThreadForm>({
        resolver: zodResolver(threadSchema),
        defaultValues: {thread_type: 'question', title: '', body: '', ai_search: false}
    })
    const commentForm = useForm<CommentForm>({resolver: zodResolver(commentSchema)})
    const aiSearch = threadForm.watch('ai_search')
    const refresh = () => queryClient.invalidateQueries({queryKey: ['case', caseId, 'discussions']})
    const createThread = useMutation({
        mutationFn: (data: ThreadForm) => api.createDiscussionThread(caseId, {
            ...data,
            evidence_ids: evidenceIds,
            person_ids: personIds
        }),
        onSuccess: async (thread) => {
            threadForm.reset({thread_type: 'question', title: '', body: '', ai_search: false});
            setEvidenceIds([]);
            setPersonIds([]);
            setCreating(false);
            setSelectedId(thread.id);
            await refresh()
        },
    })
    const addComment = useMutation({
        mutationFn: (data: CommentForm) => api.addDiscussionComment(caseId, selectedId!, data),
        onSuccess: async () => {
            commentForm.reset();
            await refresh()
        },
    })
    const react = useMutation({
        mutationFn: ({threadId, commentId, emoji}: {
            threadId: string;
            commentId: string;
            emoji: string
        }) => api.toggleDiscussionReaction(caseId, threadId, commentId, emoji),
        onSuccess: refresh,
    })
    const vote = useMutation({
        mutationFn: (threadId: string) => api.toggleDiscussionVote(caseId, threadId),
        onSuccess: refresh,
    })

    if (query.isLoading) return <div className="grid min-h-64 place-items-center"><Sparkles
        className="animate-pulse text-accent"/></div>
    if (selected) return <ThreadView caseId={caseId} thread={selected} onBack={() => setSelectedId(null)}
                                     commentForm={commentForm}
                                     submitComment={commentForm.handleSubmit((data) => addComment.mutate(data))}
                                     commenting={addComment.isPending} commentError={addComment.error}
                                      readOnly={readOnly} onVote={() => vote.mutate(selected.id)}
                                      voting={vote.isPending && vote.variables === selected.id}
                                      voteError={vote.error}
                                      onReact={(commentId, emoji) => react.mutate({
                                         threadId: selected.id,
                                         commentId,
                                         emoji
                                     })}/>

    const stats = [
        {value: totalThreads, label: totalThreads === 1 ? 'Thread' : 'Threads', tone: 'text-accent'},
        {
            value: discussionStats?.active_count ?? 0,
            label: 'Active',
            tone: 'text-teal'
        },
        {
            value: discussionStats?.source_link_count ?? 0,
            label: 'Source links',
            tone: 'text-blue'
        },
        {
            value: discussionStats?.comment_count ?? 0,
            label: 'Comments',
            tone: 'text-secondary'
        },
    ]

    return <section>
        <div className="border-b border-subtle pb-5">
            <div className="flex items-end justify-between gap-4">
                <div><p className="eyebrow">Investigator notes</p>
                    <div className="mt-2 flex items-center gap-3"><span className="h-px w-8 bg-accent"/><h2
                        className="section-title">Discussion threads</h2></div>
                    <p className="mt-2 max-w-2xl text-[15px] text-secondary">Keep each topic focused. Claims and
                        theories should identify their supporting sources.</p></div>
                {readOnly ? <Link to="/login" className="secondary-button shrink-0 text-xs">Sign in to contribute</Link> : <button type="button" onClick={() => setCreating((value) => !value)}
                        className="secondary-button shrink-0 text-xs"><Plus
                    size={16}/>{creating ? 'Close' : 'New thread'}</button>}
            </div>
            {threads.length > 0 &&
                <div className="mt-5 flex gap-2 overflow-x-auto pb-1"><span className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-accent/30 bg-accent-muted px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[.08em] text-accent"><ChevronUp size={12}/> Top voted first</span>{stats.map((stat) => <span key={stat.label}
                                                                                                 className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-default bg-tertiary/70 px-2.5 py-1.5 text-[10px] font-semibold uppercase tracking-[.08em] text-muted"><strong
                    className={stat.tone}>{stat.value}</strong>{stat.label}</span>)}</div>}
        </div>

        <MutationError error={vote.error}/>

        {creating && <form onSubmit={threadForm.handleSubmit((data) => createThread.mutate(data))}
                           className="card mt-5 border-default p-5 sm:p-6">
            <div className="grid gap-5 sm:grid-cols-[180px_1fr]">
                <label className="block text-sm font-semibold text-primary">Thread type<select
                    disabled={aiSearch} className="field mt-2 disabled:cursor-not-allowed disabled:opacity-60" {...threadForm.register('thread_type')}>
                    <option value="question">Open question</option>
                    <option value="theory">Theory</option>
                    <option value="evidence">Evidence-backed</option>
                    <option value="dispute">Contradiction / dispute</option>
                </select></label>
                <label className="block text-sm font-semibold text-primary">Short title<input className="field mt-2"
                                                                                              placeholder="What detail deserves a closer look?" {...threadForm.register('title')}/>{threadForm.formState.errors.title &&
                    <span className="mt-1 block text-xs text-danger">{threadForm.formState.errors.title.message}</span>}
                </label>
            </div>
            <label className="mt-5 flex cursor-pointer gap-3 rounded-xl border border-accent/25 bg-accent-muted/40 p-4">
                <input type="checkbox" className="mt-1 h-4 w-4 accent-current" {...threadForm.register('ai_search')}/>
                <span><span className="flex items-center gap-2 text-sm font-semibold text-primary"><Sparkles size={15} className="text-accent"/>Research this theory with AI</span>
                    <span className="mt-1 block text-xs leading-5 text-secondary">AI will use the case title, current summary, and thread title to search public sources. The result explores the theory and does not claim it is proven.</span></span>
            </label>
            {!aiSearch && <label className="mt-5 block text-sm font-semibold text-primary">Opening text<textarea
                className="field mt-2 min-h-32 resize-y py-3"
                placeholder="Explain the topic, distinguish facts from theory, and include sources when possible." {...threadForm.register('body')}/>{threadForm.formState.errors.body &&
                <span className="mt-1 block text-xs text-danger">{threadForm.formState.errors.body.message}</span>}
            </label>}
            {aiSearch && <p className="mt-4 rounded-lg border border-warning/25 bg-warning/10 px-4 py-3 text-xs leading-5 text-secondary"><strong className="text-warning">Unproven theory.</strong> Search results may provide context for or against the idea. They do not prove the allegation.</p>}
            <div className="mt-5 grid gap-3 md:grid-cols-2"><EvidencePicker caseId={caseId} selected={evidenceIds}
                                                                            onToggle={(id) => setEvidenceIds((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id])}/><PersonPicker
                caseId={caseId} selected={personIds}
                onToggle={(id) => setPersonIds((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id])}/>
            </div>
            <MutationError error={createThread.error}/>
            <button disabled={createThread.isPending} className="primary-button mt-5 text-xs">{aiSearch ? <Sparkles
                size={15}/> : <MessageCircle size={15}/>} {createThread.isPending ? (aiSearch ? 'Researching…' : 'Creating…') : (aiSearch ? 'Research and create thread' : 'Create thread')}</button>
        </form>}

        {threads.length ?
            <div className="mt-5 space-y-3">{threads.map((thread) => <ThreadCard key={thread.id} thread={thread}
                                                                                  readOnly={readOnly}
                                                                                  voting={vote.isPending && vote.variables === thread.id}
                                                                                  onVote={() => vote.mutate(thread.id)}
                                                                                  onOpen={() => setSelectedId(thread.id)}/>)}{query.hasNextPage && <div className="flex justify-center pt-2"><button type="button" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage} className="secondary-button text-xs"><ChevronDown size={15}/>{query.isFetchingNextPage ? 'Loading threads…' : 'Load more threads'}</button></div>}</div> : !creating &&
            <div className="card mt-5 grid min-h-56 place-items-center p-8 text-center">
                <div><MessageCircle className="mx-auto text-muted"/><h3 className="empty-title mt-4">No threads yet</h3>
                    <p className="mt-2 font-display text-lg text-secondary">Questions become useful when they stay
                        connected to evidence.</p><p className="mt-2 text-sm text-muted">Start the first focused
                        discussion for this case.</p></div>
            </div>}
    </section>
}

function ThreadCard({thread, onOpen, onVote, voting, readOnly}: { thread: DiscussionThread; onOpen: () => void; onVote: () => void; voting: boolean; readOnly: boolean }) {
    const style = threadTypes[thread.thread_type]
    return <article className={`group relative block w-full overflow-hidden rounded-xl border border-default border-l-2 ${style.edge} bg-tertiary/75 p-5 text-left shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-strong hover:bg-elevated/90 ${style.glow}`}>
        <div className="flex items-center justify-between gap-3">
            <div className="flex flex-wrap gap-2"><span
                className={`inline-flex rounded-md border px-2 py-1 text-[10px] font-bold uppercase tracking-[.11em] ${style.badge}`}>{style.label}</span>{thread.ai_generated &&
                <span className="ai-label">AI suggested</span>}</div>
            <div className="flex shrink-0 items-center gap-2"><button type="button" onClick={onVote} disabled={readOnly || voting} title={readOnly ? 'Sign in to vote. Votes rank topics and do not verify claims.' : 'Vote for this discussion topic. Votes do not verify claims.'} className={`inline-flex min-h-8 items-center gap-1 rounded-md border px-2 text-[10px] font-semibold transition ${thread.voted_by_me ? 'border-accent bg-accent-muted text-accent' : 'border-default bg-background/35 text-secondary hover:border-accent/45 hover:text-accent'}`}><ChevronUp size={13}/>{thread.vote_count}</button><span
                className="inline-flex items-center gap-1.5 rounded-md border border-default bg-background/35 px-2 py-1 text-[10px] font-semibold text-secondary"><MessageCircle
                size={12}/>{thread.comments.length} {thread.comments.length === 1 ? 'comment' : 'comments'}</span></div></div>
        <button type="button" onClick={onOpen} className="mt-4 flex w-full items-start gap-4 text-left">
            <div className="min-w-0 flex-1"><h3
                className="font-display text-[23px] font-semibold leading-tight text-primary transition group-hover:text-accent">{thread.title}</h3>
                <p className="mt-2 line-clamp-2 text-sm leading-6 text-secondary">{thread.body}</p></div>
            <ChevronRight size={18}
                          className="mt-1 shrink-0 text-muted transition group-hover:translate-x-0.5 group-hover:text-accent"/>
        </button>
        <LinkedPeople people={thread.people}/>
        <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-subtle pt-4"><AuthorMarker
            id={thread.author.id} name={thread.author.display_name}/><MetaChip
            icon={MessageCircle}>{thread.comments.length} replies</MetaChip><MetaChip
            icon={FileText}>{thread.evidence.length + thread.sources.length} sources</MetaChip><MetaChip
            icon={Clock3}>Updated {relativeDate(thread.updated_at)}</MetaChip></div>
    </article>
}

function ThreadView({caseId, thread, onBack, commentForm, submitComment, commenting, commentError, onReact, onVote, voting, voteError, readOnly}: {
    caseId: string;
    thread: DiscussionThread;
    onBack: () => void;
    commentForm: ReturnType<typeof useForm<CommentForm>>;
    submitComment: () => void;
    commenting: boolean;
    commentError: Error | null;
    onReact: (commentId: string, emoji: string) => void;
    onVote: () => void;
    voting: boolean;
    voteError: Error | null;
    readOnly: boolean
}) {
    const style = threadTypes[thread.thread_type]
    return <section>
        <button type="button" onClick={onBack} className="ghost-button px-0 text-xs"><ArrowLeft size={15}/> All threads
        </button>
        <article
            className={`mt-3 rounded-xl border border-default border-l-2 ${style.edge} bg-tertiary/75 p-6 shadow-card sm:p-8`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex flex-wrap gap-2"><span
                    className={`inline-flex rounded-md border px-2 py-1 text-[10px] font-bold uppercase tracking-[.11em] ${style.badge}`}>{style.label}</span>{thread.ai_generated &&
                    <span className="ai-label">AI suggested</span>}</div>
                <div className="flex flex-wrap items-center gap-3"><button type="button" onClick={onVote} disabled={readOnly || voting} title={readOnly ? 'Investigator access is required to vote' : 'Votes rank topics and do not verify claims'} className={`secondary-button min-h-9 w-auto px-3 text-xs ${thread.voted_by_me ? 'border-accent/50 bg-accent-muted text-accent' : ''}`}><ChevronUp size={14}/>{thread.vote_count} {thread.vote_count === 1 ? 'vote' : 'votes'}</button><span className="metadata">Updated {relativeDate(thread.updated_at)}</span></div></div>
            <h2 className="page-title mt-4">{thread.title}</h2><p
            className="mt-5 whitespace-pre-line text-[15px] leading-7 text-secondary">{thread.body}</p>{thread.ai_generated &&
            <p className="mt-3 text-[10px] leading-5 text-muted">Generated as a research prompt from public sources. It
                is not a verified conclusion.</p>}<LinkedPeople people={thread.people}/>{thread.sources.length > 0 &&
            <div className="mt-6"><p className="eyebrow">Supporting sources</p>
                <div className="mt-3 flex flex-wrap gap-2">{thread.sources.map((source) => <a key={source.id}
                                                                                              href={source.url}
                                                                                              target="_blank"
                                                                                              rel="noreferrer"
                                                                                              className="inline-flex items-center gap-1.5 rounded-md border border-info/30 px-2.5 py-1.5 text-[10px] text-blue hover:border-info/50"><FileText
                    size={12}/>{source.publisher || source.title}</a>)}</div>
            </div>}{thread.evidence.length > 0 && <div className="mt-6"><p className="eyebrow">Linked evidence</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-2">{thread.evidence.map((item) => <EvidenceCard key={item.id}
                                                                                                         caseId={caseId}
                                                                                                         item={item}
                                                                                                         compact/>)}</div>
        </div>}
            <div className="mt-6 border-t border-subtle pt-4"><AuthorMarker id={thread.author.id}
                                                                            name={thread.author.display_name}/></div>
        </article>
        <MutationError error={voteError}/>
        <div className="mt-6"><p className="eyebrow">Case discussion</p><h3
            className="section-title mt-1">{thread.comments.length} {thread.comments.length === 1 ? 'comment' : 'comments'}</h3>
        </div>
        <div className="mt-4 space-y-3 border-l border-default pl-3 sm:pl-5">{thread.comments.map((comment) =>
            <CommentCard key={comment.id} comment={comment} readOnly={readOnly} onReact={(emoji) => onReact(comment.id, emoji)}/>)}</div>
        {readOnly ? <div className="mt-5"><Link to="/login" className="secondary-button w-full text-xs">Sign in to join this discussion</Link></div> : <form onSubmit={submitComment} className="card mt-5 border-default p-5"><label
            className="block text-sm font-semibold text-primary">Add a comment<textarea
            className="field mt-2 min-h-28 resize-y py-3"
            placeholder="Add information, a question, or a sourced correction…" {...commentForm.register('body')}/>{commentForm.formState.errors.body &&
            <span className="mt-1 block text-xs text-danger">{commentForm.formState.errors.body.message}</span>}</label><MutationError
            error={commentError}/>
            <button disabled={commenting} className="primary-button mt-4 text-xs"><Send
                size={15}/>{commenting ? 'Posting…' : 'Post comment'}</button>
        </form>}
    </section>
}

function CommentCard({comment, onReact, readOnly}: { comment: DiscussionComment; onReact: (emoji: string) => void; readOnly: boolean }) {
    return <article
        className="rounded-xl border border-subtle bg-surface/90 p-5 transition duration-200 hover:border-default">
        <div className="flex items-start justify-between gap-3"><AuthorMarker id={comment.author.id}
                                                                               name={comment.author.display_name}/>
            <div className="flex shrink-0 items-center gap-1"><ReportButton resourceType="discussion_comment" resourceId={comment.id}/><time className="metadata text-[10px]">{formatDate(comment.created_at)}</time></div>
        </div>
        <p className="mt-4 whitespace-pre-line text-sm leading-6 text-primary">{comment.body}</p>
        <div className="mt-4 flex flex-wrap gap-2 border-t border-subtle pt-3"
             aria-label="Comment reactions">{reactionOptions.map((emoji) => {
            const reaction = comment.reactions.find((item) => item.emoji === emoji);
            return <button type="button" key={emoji} disabled={readOnly} title={readOnly ? 'Sign in to react' : undefined} onClick={() => onReact(emoji)} aria-label={`React ${emoji}`}
                           className={`min-h-9 rounded-md border px-2.5 text-sm transition duration-200 ${reaction?.reacted_by_me ? 'border-accent bg-accent-muted' : 'border-subtle bg-background/30 hover:border-default hover:bg-white/[.035]'}`}>{emoji}{reaction &&
                <span className="ml-1 text-[10px] text-muted">{reaction.count}</span>}</button>
        })}</div>
    </article>
}

function AuthorMarker({id, name}: { id: string; name: string }) {
    const initials = name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
    return <Link to={`/users/${id}`} onClick={(event) => event.stopPropagation()}
                 className="inline-flex min-w-0 items-center gap-2"><span
        className="grid size-7 shrink-0 place-items-center rounded-full border border-default bg-elevated text-[9px] font-bold text-accent">{initials}</span><span
        className="min-w-0"><span
        className="block truncate text-[11px] font-semibold text-primary hover:text-accent">{name}</span><span
        className="block text-[9px] font-semibold uppercase tracking-[.1em] text-muted">Contributor</span></span></Link>
}

function MetaChip({icon: Icon, children}: { icon: typeof MessageCircle; children: ReactNode }) {
    return <span
        className="inline-flex min-h-7 items-center gap-1.5 rounded-md border border-subtle bg-background/30 px-2 text-[10px] font-medium text-muted"><Icon
        size={11}/>{children}</span>
}

function MutationError({error}: { error: Error | null }) {
    return error ? <p role="alert"
                      className="mt-4 text-xs text-danger">{error instanceof ApiError ? error.message : 'The discussion could not be updated'}</p> : null
}

function formatDate(value: string) {
    return new Intl.DateTimeFormat(undefined, {dateStyle: 'medium', timeStyle: 'short'}).format(new Date(value))
}

function relativeDate(value: string) {
    const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
    const ranges: [number, Intl.RelativeTimeFormatUnit][] = [[60, 'second'], [60, 'minute'], [24, 'hour'], [7, 'day'], [4.345, 'week'], [12, 'month'], [Number.POSITIVE_INFINITY, 'year']];
    let amount = seconds;
    for (const [divisor, unit] of ranges) {
        if (Math.abs(amount) < divisor) return new Intl.RelativeTimeFormat(undefined, {numeric: 'auto'}).format(Math.round(amount), unit);
        amount /= divisor
    }
    return formatDate(value)
}
