import { useMutation, useQuery } from '@tanstack/react-query'
import { Ban, CheckCircle2, ChevronLeft, ChevronRight, Eye, EyeOff, Flag, RotateCcw, ShieldAlert, XCircle } from 'lucide-react'
import { useState } from 'react'
import { PageHeader, StatusBadge } from '../../components/ui/Visual'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'
import type { ModerationReport } from '../../types'

type Action = 'hide' | 'restore' | 'lock_user' | 'unlock_user' | 'resolve' | 'dismiss'

export function ModerationQueuePage() {
  const [status, setStatus] = useState('pending')
  const [page, setPage] = useState(1)
  const reports = useQuery({ queryKey: ['admin', 'reports', status, page], queryFn: () => api.adminReports(status, page) })
  const decision = useMutation({
    mutationFn: ({ reportId, action }: { reportId: string; action: Action }) => {
      const note = ['resolve', 'dismiss'].includes(action) ? window.prompt('Optional moderation note') ?? undefined : undefined
      return api.moderateReport(reportId, action, note)
    },
    onSuccess: async () => { await queryClient.invalidateQueries({ queryKey: ['admin', 'reports'] }) },
  })
  const act = (report: ModerationReport, action: Action) => {
    const dangerous = action === 'lock_user' || action === 'hide'
    if (!dangerous || window.confirm(action === 'lock_user' ? 'Lock this user pending review and revoke all active sessions?' : 'Hide this content from the application pending review?')) decision.mutate({ reportId: report.id, action })
  }

  return <div>
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><PageHeader eyebrow="Administration" title="Moderation queue" description="Review reports with context before restricting content or accounts."/><StatusBadge tone="danger"><ShieldAlert size={14}/> Moderator access</StatusBadge></div>
    <div className="mt-7 flex gap-2 overflow-x-auto">{['pending', 'resolved', 'dismissed', ''].map((value) => <button type="button" key={value || 'all'} onClick={() => { setStatus(value); setPage(1) }} className={status === value ? 'primary-button min-h-10 w-auto shrink-0 px-4 text-xs' : 'secondary-button min-h-10 w-auto shrink-0 px-4 text-xs'}>{value || 'all'}</button>)}</div>
    {decision.error && <p role="alert" className="error-banner mt-5">{decision.error instanceof ApiError ? decision.error.message : 'The moderation action failed'}</p>}
    {reports.isLoading ? <div className="grid min-h-64 place-items-center"><Flag className="animate-pulse text-accent"/></div> : reports.error ? <p role="alert" className="error-banner mt-6">Reports could not be loaded.</p> : reports.data?.items.length ? <div className="mt-6 space-y-4">{reports.data.items.map((report) => {
      const contentTarget = report.resource_type !== 'user'
      return <article key={report.id} className="card p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3"><div className="flex flex-wrap gap-2"><StatusBadge tone={report.status === 'pending' ? 'warning' : report.status === 'resolved' ? 'success' : 'neutral'}>{report.status}</StatusBadge><StatusBadge tone="danger">{report.reason_code.replaceAll('_', ' ')}</StatusBadge><StatusBadge>{report.resource_type.replaceAll('_', ' ')}</StatusBadge></div><time className="metadata">{new Date(report.created_at).toLocaleString()}</time></div>
        <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-6 text-primary">{report.target_summary}</p>
        <div className="mt-4 rounded-lg border border-subtle bg-background/35 p-4"><p className="eyebrow">Reporter statement</p><p className="mt-2 whitespace-pre-wrap text-xs leading-5 text-secondary">{report.details}</p><p className="metadata mt-3 text-[9px]">Reported by {report.reporter_email}</p></div>
        <div className="mt-5 flex flex-wrap gap-2">{contentTarget && <><button type="button" onClick={() => act(report, 'hide')} className="danger-button min-h-10 w-auto px-3 text-xs"><EyeOff size={14}/>Hide pending review</button><button type="button" onClick={() => act(report, 'restore')} className="secondary-button min-h-10 w-auto px-3 text-xs"><Eye size={14}/>Restore</button></>}{report.target_user_id && <><button type="button" onClick={() => act(report, 'lock_user')} className="danger-button min-h-10 w-auto px-3 text-xs"><Ban size={14}/>Lock user</button><button type="button" onClick={() => act(report, 'unlock_user')} className="secondary-button min-h-10 w-auto px-3 text-xs"><RotateCcw size={14}/>Unlock</button></>}<button type="button" onClick={() => act(report, 'resolve')} className="secondary-button min-h-10 w-auto border-success/35 px-3 text-xs text-success"><CheckCircle2 size={14}/>Resolve</button><button type="button" onClick={() => act(report, 'dismiss')} className="ghost-button min-h-10 w-auto px-3 text-xs"><XCircle size={14}/>Dismiss</button></div>
      </article>
    })}</div> : <div className="card mt-7 p-10 text-center"><ShieldAlert className="mx-auto text-muted"/><h2 className="empty-title mt-4">Queue clear</h2><p className="mt-2 text-sm text-muted">No reports match this status.</p></div>}
    {reports.data && reports.data.total_pages > 1 && <nav className="mt-7 flex items-center justify-between gap-4" aria-label="Moderation pages"><button type="button" disabled={!reports.data.has_previous} onClick={() => setPage((value) => value - 1)} className="secondary-button text-xs"><ChevronLeft size={15}/>Previous</button><span className="metadata">Page {page} of {reports.data.total_pages}</span><button type="button" disabled={!reports.data.has_next} onClick={() => setPage((value) => value + 1)} className="secondary-button text-xs">Next<ChevronRight size={15}/></button></nav>}
  </div>
}
