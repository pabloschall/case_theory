import { useMutation, useQuery } from '@tanstack/react-query'
import { CalendarDays, LockKeyhole, Pencil, Plus, Save, Trash2, X } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router'
import { UpgradeButton } from '../../components/ui/Visual'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'
import type { CaseTimelineEntry } from '../../types'

const today = () => new Date().toISOString().slice(0, 10)

export function MyTimelinePanel({ caseId, canWrite, isAuthenticated }: { caseId: string; canWrite: boolean; isAuthenticated: boolean }) {
  const [open, setOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [occurredOn, setOccurredOn] = useState(today())
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const queryKey = ['case', caseId, 'my-timeline']
  const query = useQuery({ queryKey, queryFn: () => api.caseTimelineEntries(caseId), enabled: isAuthenticated })
  const refresh = () => queryClient.invalidateQueries({ queryKey })
  const reset = () => {
    setOpen(false)
    setEditingId(null)
    setOccurredOn(today())
    setTitle('')
    setBody('')
  }
  const creation = useMutation({
    mutationFn: () => api.createCaseTimelineEntry(caseId, { occurred_on: occurredOn, title, body }),
    onSuccess: async () => { reset(); await refresh() },
  })
  const update = useMutation({
    mutationFn: () => api.updateCaseTimelineEntry(caseId, editingId!, { occurred_on: occurredOn, title, body }),
    onSuccess: async () => { reset(); await refresh() },
  })
  const deletion = useMutation({
    mutationFn: (entryId: string) => api.deleteCaseTimelineEntry(caseId, entryId),
    onSuccess: refresh,
  })
  const edit = (entry: CaseTimelineEntry) => {
    setEditingId(entry.id)
    setOccurredOn(entry.occurred_on)
    setTitle(entry.title)
    setBody(entry.body)
    setOpen(true)
  }
  const save = () => {
    if (!occurredOn || !title.trim() || !body.trim()) return
    if (editingId) update.mutate()
    else creation.mutate()
  }
  const pending = creation.isPending || update.isPending
  const error = creation.error || update.error || deletion.error
  const entries = query.data ?? []

  return <section>
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="eyebrow">Private workspace</p><h2 className="section-title mt-2">My Timeline{entries.length > 0 && <span className="ml-2 font-ui text-xs font-medium text-muted">{entries.length}</span>}</h2><p className="mt-2 max-w-2xl text-[15px] leading-6 text-secondary">Keep a private dated record of your observations and lines of inquiry.</p></div>
      {!isAuthenticated ? <Link to="/login" className="secondary-button text-xs">Sign in</Link> : canWrite ? <button type="button" onClick={() => { reset(); setOpen(true) }} className="primary-button w-auto px-4 text-xs"><Plus size={15}/>New entry</button> : <UpgradeButton description="Creating private timeline entries is available with a paid plan.">New entry</UpgradeButton>}
    </div>
    <div className="mt-3 flex items-center gap-2 text-[10px] font-medium text-muted"><LockKeyhole size={12} className="text-accent"/>Private to you. Other investigators and the case owner cannot see this timeline.</div>

    {open && <div className="card mt-6 p-5 sm:p-6">
      <div className="flex items-center justify-between gap-3"><p className="eyebrow">{editingId ? 'Edit timeline entry' : 'New timeline entry'}</p><button type="button" onClick={reset} className="ghost-button size-9 p-0" aria-label="Close editor"><X size={15}/></button></div>
      <div className="mt-4 grid gap-4 sm:grid-cols-[180px_1fr]"><label className="text-[10px] font-semibold uppercase tracking-[.12em] text-muted">Date<input type="date" value={occurredOn} onChange={(event) => setOccurredOn(event.target.value)} className="field mt-2"/></label><label className="text-[10px] font-semibold uppercase tracking-[.12em] text-muted">Title<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={180} className="field mt-2" placeholder="What happened?"/></label></div>
      <label className="mt-4 block text-[10px] font-semibold uppercase tracking-[.12em] text-muted">Details<textarea value={body} onChange={(event) => setBody(event.target.value)} maxLength={20000} rows={6} className="field mt-2 resize-y py-3" placeholder="Describe the event, observation, or question…"/></label>
      <div className="mt-4 flex justify-end"><button type="button" onClick={save} disabled={pending || !occurredOn || !title.trim() || !body.trim()} className="primary-button w-auto px-4 text-xs"><Save size={15}/>{pending ? 'Saving…' : 'Save entry'}</button></div>
    </div>}

    {error && <p role="alert" className="error-banner mt-5">{error instanceof ApiError ? error.message : 'The timeline entry could not be saved'}</p>}
    {!isAuthenticated ? <div className="card mt-6 grid min-h-56 place-items-center p-8 text-center"><div><LockKeyhole className="mx-auto text-muted"/><h3 className="empty-title mt-4">Sign in to view your timeline</h3><p className="mt-2 text-sm text-muted">Your private case timeline is available after you sign in.</p></div></div> : query.isLoading ? <div className="card mt-6 h-56 animate-pulse"/> : query.error ? <p role="alert" className="error-banner mt-6">Your private timeline could not be loaded.</p> : entries.length ? <div className="relative mt-7 space-y-5 before:absolute before:bottom-3 before:left-[7px] before:top-3 before:w-px before:bg-subtle">{entries.map((entry) => <article key={entry.id} className="relative pl-8"><span className="absolute left-0 top-2 size-[15px] rounded-full border-4 border-background bg-accent"/><div className="card p-5 sm:p-6"><div className="flex items-start justify-between gap-4"><div><time className="text-[10px] font-semibold uppercase tracking-[.12em] text-accent">{formatDay(entry.occurred_on)}</time><h3 className="mt-2 font-display text-xl text-primary">{entry.title}</h3><p className="metadata mt-2 text-[9px]">Updated {formatDate(entry.updated_at)}</p></div>{entry.can_edit && canWrite && <span className="flex shrink-0 gap-1"><button type="button" onClick={() => edit(entry)} className="ghost-button size-9 p-0" aria-label="Edit timeline entry"><Pencil size={14}/></button><button type="button" onClick={() => { if (window.confirm('Delete this timeline entry?')) deletion.mutate(entry.id) }} className="ghost-button size-9 p-0 text-danger" aria-label="Delete timeline entry"><Trash2 size={14}/></button></span>}</div><p className="mt-4 whitespace-pre-line text-sm leading-7 text-secondary">{entry.body}</p></div></article>)}</div> : <div className="card mt-6 grid min-h-56 place-items-center p-8 text-center"><div><CalendarDays className="mx-auto text-muted"/><h3 className="empty-title mt-4">Your timeline is empty</h3><p className="mt-2 text-sm text-muted">Your private timeline entries for this case will appear here.</p></div></div>}
  </section>
}

function formatDay(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'long', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
