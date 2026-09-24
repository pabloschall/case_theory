import { useInfiniteQuery, useMutation } from '@tanstack/react-query'
import { ChevronDown, Eye, File, Link2, LockKeyhole, MessageCircle, Send, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'
import type { Evidence } from '../../types'
import { EvidenceViewer } from './EvidenceViewer'
import { ReportButton } from '../moderation/ReportButton'

export function EvidenceCard({ caseId, item, compact = false, canComment = false }: { caseId: string; item: Evidence; compact?: boolean; canComment?: boolean }) {
  const [viewerOpen, setViewerOpen] = useState(false)
  const [commentsOpen, setCommentsOpen] = useState(false)
  const locked = !item.source_url && !item.original_filename && !item.mime_type
  return <><article className={`min-w-0 max-w-full overflow-hidden rounded-xl border border-subtle bg-background/40 transition duration-200 hover:border-strong ${compact ? 'p-3' : 'p-4'}`}>
    <div className="flex min-w-0 items-start gap-3">
      <span className="grid size-10 shrink-0 place-items-center rounded-lg border border-info/25 bg-blue-muted text-blue">{item.source_url ? <Link2 size={17}/> : <File size={17}/>}</span>
      <button type="button" onClick={locked ? undefined : () => setViewerOpen(true)} disabled={item.processing_status !== 'available'} title={locked ? 'Upgrade to inspect this evidence item' : 'View evidence inside Case Theory'} className="group min-w-0 flex-1 overflow-hidden text-left disabled:opacity-50">
        <span className="flex min-w-0 flex-wrap items-start gap-2"><span className="min-w-0 flex-1 break-words text-xs font-semibold text-primary [overflow-wrap:anywhere]">{item.title}</span>{item.ai_generated && <span className="ai-label shrink-0">AI suggested</span>}</span>
        <span className="metadata mt-1 block whitespace-normal break-words text-[10px] text-blue [overflow-wrap:anywhere]">{item.original_filename || host(item.source_url)} · {item.verification_status}</span>
        {!compact && item.description && <span className="mt-2 line-clamp-3 block break-words text-xs leading-5 text-secondary [overflow-wrap:anywhere]">{item.description}</span>}
        {!compact && item.ai_generated && <span className="mt-2 block break-words text-[10px] leading-4 text-muted [overflow-wrap:anywhere]">Selected from public research for review; inclusion does not verify every claim in the source.</span>}
      </button>
      {locked ? <LockKeyhole size={14} className="mt-1 shrink-0 text-accent"/> : <Eye size={15} className="mt-1 shrink-0 text-muted"/>}
    </div>
    {!compact && <div className="mt-4 border-t border-subtle pt-3">
      <div className="flex items-center justify-between gap-3"><button type="button" onClick={() => setCommentsOpen((open) => !open)} className="ghost-button min-h-9 px-2 text-[11px]">
        <MessageCircle size={14}/> {item.comment_count || 0} {(item.comment_count || 0) === 1 ? 'comment' : 'comments'} <ChevronDown size={13} className={`transition ${commentsOpen ? 'rotate-180' : ''}`}/>
      </button><ReportButton resourceType="evidence" resourceId={item.id} label="Flag evidence"/></div>
      {commentsOpen && <EvidenceComments caseId={caseId} evidenceId={item.id} canComment={canComment}/>} 
    </div>}
  </article>{viewerOpen && <EvidenceViewer caseId={caseId} item={item} onClose={() => setViewerOpen(false)}/>}</>
}

function EvidenceComments({ caseId, evidenceId, canComment }: { caseId: string; evidenceId: string; canComment: boolean }) {
  const [body, setBody] = useState('')
  const queryKey = ['case', caseId, 'evidence', evidenceId, 'comments']
  const query = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => api.evidenceComments(caseId, evidenceId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  })
  const comments = query.data?.pages.flatMap((page) => page.items) ?? []
  const refresh = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey }),
      queryClient.invalidateQueries({ queryKey: ['case', caseId, 'evidence'] }),
    ])
  }
  const creation = useMutation({
    mutationFn: () => api.createEvidenceComment(caseId, evidenceId, body),
    onSuccess: async () => { setBody(''); await refresh() },
  })
  const deletion = useMutation({ mutationFn: (commentId: string) => api.deleteEvidenceComment(caseId, evidenceId, commentId), onSuccess: refresh })

  return <div className="mt-3 rounded-lg border border-subtle bg-surface/65 p-3">
    {canComment && <form onSubmit={(event) => { event.preventDefault(); if (body.trim()) creation.mutate() }}>
      <label className="sr-only" htmlFor={`evidence-comment-${evidenceId}`}>Add a comment</label>
      <textarea id={`evidence-comment-${evidenceId}`} value={body} onChange={(event) => setBody(event.target.value)} maxLength={3000} rows={3} className="field min-h-20 resize-y text-xs" placeholder="Add an observation, question, or source note…"/>
      <div className="mt-2 flex items-center justify-between gap-3"><span className="metadata text-[9px]">{body.length}/3000</span><button type="submit" disabled={!body.trim() || creation.isPending} className="primary-button min-h-9 w-auto px-3 text-[11px]"><Send size={13}/>{creation.isPending ? 'Posting…' : 'Comment'}</button></div>
    </form>}
    {!canComment && <p className="text-[11px] leading-5 text-muted">Sign in with contributor access to add a comment.</p>}
    {creation.error && <p role="alert" className="mt-2 text-[11px] text-danger-text">{creation.error instanceof ApiError ? creation.error.message : 'Comment could not be posted'}</p>}
    {query.isLoading ? <p className="mt-3 animate-pulse text-[11px] text-muted">Loading comments…</p> : comments.length ? <div className={`${canComment ? 'mt-4 border-t border-subtle pt-3' : 'mt-3'} space-y-3`}>{comments.map((comment) => <div key={comment.id} className="group/comment">
      <div className="flex items-start justify-between gap-3"><p className="text-[11px] font-semibold text-primary">{comment.author.display_name} <span className="font-normal text-muted">@{comment.author.username}</span></p><div className="flex items-center"><ReportButton resourceType="evidence_comment" resourceId={comment.id}/>{comment.can_delete && <button type="button" onClick={() => { if (window.confirm('Delete this evidence comment?')) deletion.mutate(comment.id) }} disabled={deletion.isPending && deletion.variables === comment.id} className="ghost-button min-h-7 px-2 text-danger-text" aria-label="Delete comment"><Trash2 size={12}/></button>}</div></div>
      <p className="mt-1 whitespace-pre-wrap break-words text-xs leading-5 text-secondary">{comment.body}</p><p className="metadata mt-1 text-[9px]">{new Date(comment.created_at).toLocaleString()}</p>
    </div>)}</div> : <p className={`${canComment ? 'mt-4 border-t border-subtle pt-3' : 'mt-3'} text-[11px] text-muted`}>No comments yet. Start with a sourced observation or question.</p>}
    {deletion.error && <p role="alert" className="mt-2 text-[11px] text-danger-text">{deletion.error instanceof ApiError ? deletion.error.message : 'Comment could not be deleted'}</p>}
    {query.hasNextPage && <button type="button" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage} className="secondary-button mt-3 min-h-9 w-full text-[11px]"><ChevronDown size={13}/>{query.isFetchingNextPage ? 'Loading…' : 'Load more comments'}</button>}
  </div>
}

function host(value: string | null) { try { return value ? new URL(value).hostname : 'External source' } catch { return 'External source' } }
