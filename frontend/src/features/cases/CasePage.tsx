import {ArrowLeft, Bookmark, BookmarkCheck, Eye, Globe2, LockKeyhole, RefreshCw, Sparkles} from 'lucide-react'
import {useMutation, useQuery} from '@tanstack/react-query'
import {useEffect, useRef, useState} from 'react'
import {Link, useParams} from 'react-router'
import {api} from '../../services/api'
import type {CaseDetail} from '../../types'
import {queryClient} from '../../lib/query'
import {DiscussionPanel} from '../discussion/DiscussionPanel'
import {EvidencePanel} from '../evidence/EvidencePanel'
import {TimelinePanel} from '../timeline/TimelinePanel'
import {PeoplePanel} from '../people/PeoplePanel'
import {MapPanel} from '../map/MapPanel'
import {StatusBadge, UpgradeButton, UpgradePanel} from '../../components/ui/Visual'
import {InviteCollaborators} from '../invitations/InviteCollaborators'
import {APP_NAME} from '../../config/brand'
import {MyNotesPanel} from '../notes/MyNotesPanel'
import {MyTimelinePanel} from '../timeline/MyTimelinePanel'
import {ResearcherChat} from './ResearcherChat'
import {Seo} from '../../components/Seo'

const tabs = ['Overview', 'Researcher', 'Discussion', 'Timeline', 'Evidence', 'Map', 'People', 'My Notes', 'My Timeline'] as const
type Tab = typeof tabs[number]
const generationStatuses = ['queued', 'researching_sources', 'generating_overview', 'generating_banner', 'queued_source_enrichment', 'enriching_official_source']

export function CasePage() {
    const {caseId = ''} = useParams()
    const [tab, setTab] = useState<Tab>('Overview')
    const viewedCaseId = useRef<string | null>(null)
    const query = useQuery({
        queryKey: ['case', caseId],
        queryFn: () => api.case(caseId),
        enabled: Boolean(caseId),
        refetchInterval: ({state}) => state.data?.ai_research_status && !['complete', 'failed'].includes(state.data.ai_research_status) ? 2000 : false
    })
    const {data: currentUser} = useQuery({queryKey: ['current-user'], queryFn: api.currentUser, retry: false})
    const research = useMutation({
        mutationFn: () => api.researchCase(caseId), onSuccess: async () => {
            await queryClient.invalidateQueries({queryKey: ['case', caseId]})
        }
    })
    const sourceEnrichment = useMutation({
        mutationFn: () => api.enrichFbiCase(caseId), onSuccess: async () => {
            await queryClient.invalidateQueries({queryKey: ['case', caseId]})
        }
    })
    const privacyMutation = useMutation({
        mutationFn: (privacy: 'public' | 'private') => api.updateCasePrivacy(caseId, privacy),
        onSuccess: (updated) => {
            queryClient.setQueryData(['case', caseId], updated);
            void queryClient.invalidateQueries({queryKey: ['cases']})
        }
    })
    const followMutation = useMutation({
        mutationFn: (isFollowing: boolean) => isFollowing ? api.unfollowCase(caseId) : api.followCase(caseId),
        onSuccess: ({is_following}) => {
            queryClient.setQueryData<CaseDetail>(['case', caseId], (current) => current ? {
                ...current,
                is_following
            } : current)
            void queryClient.invalidateQueries({queryKey: ['cases', 'following']})
        },
    })
    const item = query.data
    const loadedCaseId = item?.id
    const generating = Boolean(item && generationStatuses.includes(item.ai_research_status))

    useEffect(() => {
        if (!loadedCaseId || viewedCaseId.current === loadedCaseId) return
        viewedCaseId.current = loadedCaseId
        void api.recordCaseView(loadedCaseId).then(({view_count}) => {
            queryClient.setQueryData<CaseDetail>(['case', loadedCaseId], (current) => current ? {...current, view_count} : current)
            void queryClient.invalidateQueries({queryKey: ['cases']})
        }).catch(() => {})
    }, [loadedCaseId])

    if (query.isLoading) return <div className="grid min-h-[60vh] place-items-center"><Sparkles
        className="animate-pulse text-accent"/></div>
    if (!item) return <div className="card p-8 text-center text-muted"><Seo title="Case unavailable | Case Theory" description="This case is unavailable." path={`/cases/${caseId}`} noindex/>Case could not be loaded.</div>
    const importedFromFbi = item.external_sources.some((source) => source.source_type === 'fbi')
    const caseMetadata = [item.year, item.location].filter(Boolean).join(' · ')
    const canResearch = currentUser?.permissions.includes('ai.research') ?? false
    const isAdmin = currentUser?.permissions.includes('admin.access') ?? false
    const canUseResearcher = canResearch && (isAdmin || (currentUser?.tier_level ?? 0) >= 2)
    const canInvite = currentUser?.permissions.includes('case.invite') ?? false
    const canWriteTimeline = currentUser?.permissions.includes('timeline.write') ?? false
    const canWritePrivateTimeline = currentUser?.permissions.includes('timeline.private_write') ?? false
    const canUploadEvidence = currentUser?.permissions.includes('evidence.upload') ?? false
    const canWriteDiscussion = currentUser?.permissions.includes('discussion.write') ?? false
    const canWriteMap = currentUser?.permissions.includes('map.write') ?? false
    const canViewPeople = item.privacy === 'public' || (currentUser?.permissions.includes('people.read') ?? false)
    const canWriteNotes = currentUser?.permissions.includes('notes.write') ?? false
    return <div className="min-w-0 max-w-full overflow-x-clip">
        <Seo title={`${item.title} | Case Theory`} description={(item.summary?.body || [item.title, item.year, item.location].filter(Boolean).join(' · ')).replace(/\s+/g, ' ').slice(0, 160)} path={`/cases/${item.id}`} image={item.cover_image_url} noindex={item.privacy !== 'public'}/>
        <Link to="/cases" className="ghost-button px-0 text-xs"><ArrowLeft size={15}/> Case directory</Link>
        <header className="surface relative mt-5 overflow-hidden"><img src={item.cover_image_url || '/case-banner.png'}
                                                                       alt="Symbolic editorial case banner"
                                                                       className="absolute inset-0 size-full object-cover"/>
            <div
                className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(5,8,11,.10)_0%,rgba(5,8,11,.40)_50%,rgba(11,17,23,.98)_100%)]"/>
            <div className="relative flex min-h-72 flex-col justify-end p-6 sm:min-h-80 sm:p-8">
                <div className="flex flex-wrap items-center gap-2"><StatusBadge
                    tone="ai">{item.status}</StatusBadge><span
                    className="inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-[.12em] text-secondary">{item.privacy === 'private' ?
                    <LockKeyhole size={12}/> : <Globe2 size={12}/>} {item.privacy}</span>{caseMetadata &&
                    <span className="metadata uppercase tracking-[.1em]">{caseMetadata}</span>}</div>
                <h1 className="case-title mt-4 max-w-3xl">{item.title}</h1><p
                className="mt-2 text-xs text-secondary">Owned by <span
                className="font-semibold text-primary">{item.is_owner ? 'you' : item.owner.display_name}</span>
            </p><p className="mt-2 inline-flex items-center gap-1.5 text-xs text-secondary"><Eye size={13}/>{item.view_count} {item.view_count === 1 ? 'view' : 'views'}</p>{generating &&
                <ResearchProgress status={item.ai_research_status}/>} {item.ai_research_status === 'failed' &&
                <p className="error-banner mt-4">Generation stopped: {item.ai_error_message}</p>}
                <div
                    className="mt-5 flex flex-wrap items-center gap-3">{currentUser && !item.is_owner && item.privacy === 'public' &&
                    <button type="button" onClick={() => followMutation.mutate(item.is_following)}
                            disabled={followMutation.isPending}
                            className={item.is_following ? 'secondary-button w-fit border-accent/45 text-xs text-accent' : 'primary-button w-fit px-4 text-xs'}>{item.is_following ?
                        <BookmarkCheck size={15}/> : <Bookmark
                            size={15}/>} {followMutation.isPending ? 'Updating…' : item.is_following ? 'Following' : 'Follow case'}</button>}{currentUser && item.is_owner && importedFromFbi && !generating &&
                     (canResearch ? <button type="button" onClick={() => sourceEnrichment.mutate()}
                            disabled={sourceEnrichment.isPending}
                            className="secondary-button w-fit border-accent/45 text-xs text-accent"><Sparkles
                        size={15}/>{sourceEnrichment.isPending ? 'Queuing enrichment…' : 'Enrich official source'}
                    </button> : <UpgradeButton requiredTier={3} description="AI enrichment for an existing case is available on the Lead Investigator plan.">Enrich official source</UpgradeButton>)}{isAdmin && !importedFromFbi && !generating &&
                    <button type="button" onClick={() => research.mutate()} disabled={research.isPending}
                            className="secondary-button w-fit border-accent/45 text-xs text-accent"><RefreshCw size={15}
                                                                                                                className={research.isPending ? 'animate-spin' : ''}/>{research.isPending ? 'Queuing research…' : 'Research again'}
                    </button>}{currentUser && (canInvite ?
                    <InviteCollaborators caseId={item.id}/> : <UpgradeButton description="Inviting collaborators is available on the Investigator plan.">Invite person</UpgradeButton>)} {(item.is_owner || isAdmin) && (currentUser?.permissions.includes('case.private') ? <label
                    className="inline-flex min-h-11 items-center gap-2 rounded-lg border border-default bg-background/70 px-3 text-xs text-secondary"><span>Visibility</span><select
                    value={item.privacy} disabled={privacyMutation.isPending}
                    onChange={(event) => privacyMutation.mutate(event.target.value as 'public' | 'private')}
                    className="bg-transparent font-semibold text-primary outline-none">
                    <option value="public">Public</option>
                    <option value="private" disabled={!currentUser?.permissions.includes('case.private')}>Private
                    </option>
                </select></label> : <UpgradeButton description="Private case visibility is available on the Investigator plan.">Change visibility</UpgradeButton>)}{!currentUser &&
                    <Link to="/login" className="secondary-button w-fit text-xs text-accent">Sign in to follow and
                        contribute</Link>}</div>
            </div>
        </header>
        <nav className="mt-4 flex max-w-full gap-1 overflow-x-auto border-b border-subtle">{tabs.map((value) => <button
            key={value} onClick={() => setTab(value)}
            className={`relative min-h-12 shrink-0 rounded-t-lg border-b-2 px-4 text-xs font-semibold transition duration-200 ${tab === value ? 'border-accent bg-accent-muted text-accent shadow-[inset_0_-5px_14px_rgba(213,166,74,.05)]' : 'border-transparent text-muted hover:bg-white/[.025] hover:text-primary'}`}>{value}</button>)}</nav>
        <div className="mt-6">{tab === 'Overview' && <Overview item={item}/>}<div hidden={tab !== 'Researcher'}>{canUseResearcher ? <ResearcherChat key={item.id} caseId={item.id} title={item.title}/> : <UpgradePanel title="Researcher is locked" description="Online research is available with a paid plan."/>}</div> {tab === 'Discussion' &&
            <DiscussionPanel caseId={item.id} readOnly={!canWriteDiscussion}/>} {tab === 'Timeline' &&
            <TimelinePanel item={item} readOnly={!canWriteTimeline} canReorder={item.is_owner || isAdmin}/>} {tab === 'Evidence' &&
            <EvidencePanel caseId={item.id} readOnly={!canUploadEvidence} canComment={canWriteDiscussion}/>} {tab === 'Map' && <MapPanel caseId={item.id} readOnly={!canWriteMap}/>} {tab === 'People' &&
            (canViewPeople ? <PeoplePanel caseId={item.id} readOnly={!currentUser}/> : <UpgradePanel title="People & Relationships is locked" description="This private case is available only to its members."/>)} {tab === 'My Notes' &&
            <MyNotesPanel caseId={item.id} canWrite={canWriteNotes} isAuthenticated={Boolean(currentUser)}/>} {tab === 'My Timeline' &&
            <MyTimelinePanel caseId={item.id} canWrite={canWritePrivateTimeline} isAuthenticated={Boolean(currentUser)}/>}
        </div>
    </div>
}

function Overview({item}: { item: CaseDetail }) {
    const aiSummary = item.summary && ['ai', 'user_plus_ai'].includes(item.summary.source)
    return <div className="grid gap-6 lg:grid-cols-[1.5fr_.7fr]">
        <section className="card p-6 sm:p-8">
            <div className="flex items-center justify-between gap-4"><h2 className="section-title">Case
                overview</h2>{aiSummary &&
                <span className="ai-label"><Sparkles size={12}/> AI-assisted synthesis</span>}</div>
            {item.summary ?
                <p className="mt-5 whitespace-pre-line text-[15px] leading-7 text-secondary">{item.summary.body}</p> :
                <p className="mt-5 text-sm text-muted">The sourced overview will appear here when research
                    completes.</p>}{item.external_sources.length > 0 &&
            <div className="mt-8 border-t border-subtle pt-6"><p className="eyebrow">Official source data</p>
                <div className="mt-4 space-y-3">{item.external_sources.map((source) => <a
                    key={`${source.source_type}-${source.external_id}`} href={source.source_url} target="_blank"
                    rel="noreferrer"
                    className="block rounded-lg border border-subtle bg-tertiary/50 p-4 transition hover:border-blue/40"><span
                    className="block text-xs font-semibold text-primary">{source.source_name}</span><span
                    className="metadata mt-1 block text-[10px]">Original case information · View source</span></a>)}</div>
                <p className="mt-3 text-[10px] leading-4 text-muted">{APP_NAME} is an independent platform and is not
                    affiliated with or endorsed by the Federal Bureau of Investigation.</p>
            </div>}{item.sources.length > 0 &&
            <div className="mt-8 border-t border-subtle pt-6"><p className="eyebrow">Research sources</p>
                <ol className="mt-4 space-y-3">{item.sources.map((source, index) => <li key={source.id}
                                                                                        className="flex gap-3 text-xs">
                    <span className="font-semibold text-accent">[{index + 1}]</span><a href={source.url} target="_blank"
                                                                                       rel="noreferrer"
                                                                                       className="min-w-0 text-blue hover:text-primary"><span
                    className="block font-semibold">{source.title}</span><span
                    className="metadata mt-1 block truncate text-[10px]">{source.publisher} · {source.source_type.replaceAll('_', ' ')}</span></a>
                </li>)}</ol>
            </div>}</section>
        <aside className="card h-fit p-5"><p className="eyebrow">Intake</p>
            <dl className="mt-4 divide-y divide-subtle text-xs">
                <div className="py-3">
                    <dt className="text-muted">Names</dt>
                    <dd className="mt-1 font-semibold text-primary">{item.victim_names}</dd>
                </div>
                <div className="py-3">
                    <dt className="text-muted">Year</dt>
                    <dd className="mt-1 font-semibold text-primary">{item.year ?? 'Not provided'}</dd>
                </div>
                <div className="py-3">
                    <dt className="text-muted">Location</dt>
                    <dd className="mt-1 font-semibold text-primary">{item.location || 'Not provided'}</dd>
                </div>
            </dl>
        </aside>
    </div>
}

function ResearchProgress({status}: { status: string }) {
    const label: Record<string, string> = {
        queued: 'Preparing research',
        researching_sources: 'Analyzing public sources',
        generating_overview: 'Comparing dates and building summary',
        generating_banner: 'Preparing editorial case art',
        queued_source_enrichment: 'Preparing official source',
        enriching_official_source: 'Extracting sourced people and events'
    };
    return <div className="mt-5 max-w-md"><p className="flex items-center gap-2 text-xs font-medium text-accent">
        <Sparkles size={14}/> {label[status] || 'Research in progress'}</p>
        <div className="mt-3 h-0.5 overflow-hidden bg-white/10"><span
            className="block h-full w-2/3 animate-pulse bg-accent"/></div>
    </div>
}
