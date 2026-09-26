import { useInfiniteQuery, useMutation } from '@tanstack/react-query'
import { BookOpen, ChevronDown, FilePenLine, LockKeyhole, Plus, Save, Trash2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'
import type { CaseNotebookNote } from '../../types'
import { UpgradeButton } from '../../components/ui/Visual'

export function MyNotesPanel({ caseId, canWrite, isAuthenticated }: { caseId: string; canWrite: boolean; isAuthenticated: boolean }) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const queryKey = ['case', caseId, 'notebook-notes']
  const query = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => api.notebookNotes(caseId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: isAuthenticated,
  })
  const notes = useMemo(() => query.data?.pages.flatMap((page) => page.items) ?? [], [query.data])
  const selected = notes.find((note) => note.id === selectedId) ?? null
  const total = query.data?.pages[0]?.total ?? 0

  useEffect(() => {
    if (!creating && !selectedId && notes[0]) setSelectedId(notes[0].id)
  }, [creating, notes, selectedId])

  useEffect(() => {
    if (!selected) return
    setTitle(selected.title)
    setBody(selected.body)
  }, [selected])

  const refresh = () => queryClient.invalidateQueries({ queryKey })
  const creation = useMutation({
    mutationFn: () => api.createNotebookNote(caseId, { title, body }),
    onSuccess: async (note) => {
      setCreating(false)
      setSelectedId(note.id)
      await refresh()
    },
  })
  const update = useMutation({
    mutationFn: () => api.updateNotebookNote(caseId, selectedId!, { title, body }),
    onSuccess: refresh,
  })
  const deletion = useMutation({
    mutationFn: (noteId: string) => api.deleteNotebookNote(caseId, noteId),
    onSuccess: async () => {
      setSelectedId(null)
      setTitle('')
      setBody('')
      await refresh()
    },
  })
  const pending = creation.isPending || update.isPending
  const error = creation.error || update.error || deletion.error
  const dirty = creating || Boolean(selected && (title !== selected.title || body !== selected.body))
  const canEditSelected = canWrite && Boolean(selected?.can_edit)

  const startNote = () => {
    setCreating(true)
    setSelectedId(null)
    setTitle('')
    setBody('')
  }
  const chooseNote = (note: CaseNotebookNote) => {
    if (dirty && !window.confirm('Discard your unsaved changes?')) return
    setCreating(false)
    setSelectedId(note.id)
  }
  const save = () => {
    if (!title.trim() || !body.trim()) return
    if (creating) creation.mutate()
    else if (selectedId) update.mutate()
  }

  return <section className="min-w-0">
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div><p className="eyebrow">Private workspace</p><h2 className="section-title mt-2">My Notes{total > 0 && <span className="ml-2 font-ui text-xs font-medium text-muted">{total}</span>}</h2><p className="mt-2 max-w-2xl text-[15px] leading-6 text-secondary">Keep private questions, observations, and lines of inquiry for this case.</p></div>
      {!isAuthenticated ? <Link to="/login" className="secondary-button text-xs">Sign in</Link> : canWrite ? <button type="button" onClick={startNote} className="primary-button w-auto px-4 text-xs"><Plus size={15}/>New note</button> : <UpgradeButton description="Creating private case notes is available with a paid plan.">New note</UpgradeButton>}
    </div>
    <div className="mt-3 flex items-center gap-2 text-[10px] font-medium text-muted"><LockKeyhole size={12} className="text-accent"/>Private to you. Other investigators and the case owner cannot see these notes.</div>

    {!isAuthenticated ? <div className="card mt-6 grid min-h-56 place-items-center p-8 text-center"><div><LockKeyhole className="mx-auto text-muted"/><h3 className="empty-title mt-4">Sign in to view your notes</h3><p className="mt-2 text-sm text-muted">Your private case notebook is available after you sign in.</p></div></div> : query.isLoading ? <div className="mt-6 grid gap-4 lg:grid-cols-[.65fr_1.35fr]"><div className="card h-64 animate-pulse"/><div className="card h-96 animate-pulse"/></div> : query.error ? <p role="alert" className="error-banner mt-6">{query.error instanceof ApiError ? query.error.message : 'Your notebook could not be loaded'}</p> : <div className="mt-6 grid min-w-0 gap-4 lg:grid-cols-[minmax(240px,.65fr)_minmax(0,1.35fr)]">
      <aside className="card h-fit min-w-0 overflow-hidden p-2">
        {notes.length ? <div className="space-y-1">{notes.map((note) => <button type="button" key={note.id} onClick={() => chooseNote(note)} className={`w-full min-w-0 rounded-lg border px-3 py-3 text-left transition duration-200 ${selectedId === note.id && !creating ? 'border-accent/45 bg-accent-muted' : 'border-transparent hover:border-subtle hover:bg-white/[.025]'}`}>
          <span className="block truncate text-xs font-semibold text-primary">{note.title}</span>
        </button>)}</div> : !creating && <div className="px-4 py-10 text-center"><BookOpen className="mx-auto text-muted"/><p className="mt-3 font-display text-xl text-primary">An empty notebook</p><p className="mt-2 text-xs leading-5 text-muted">Start with a question you want to answer.</p></div>}
        {query.hasNextPage && <button type="button" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage} className="ghost-button mt-2 w-full text-[10px]"><ChevronDown size={13}/>{query.isFetchingNextPage ? 'Loading…' : 'Load older notes'}</button>}
      </aside>

      {(creating || selected) ? <article className="card min-w-0 p-5 sm:p-7">
        <div className="flex items-start justify-between gap-3"><div><p className="eyebrow">{creating ? 'New notebook entry' : 'Notebook entry'}</p><p className="metadata mt-2 text-[9px]">{selected ? `Last edited ${formatDate(selected.updated_at)}` : 'Not saved yet'}</p></div>{selected && canEditSelected && <button type="button" onClick={() => { if (window.confirm('Delete this note?')) deletion.mutate(selected.id) }} disabled={deletion.isPending} className="danger-button min-h-10 w-auto px-3 text-xs" aria-label="Delete note"><Trash2 size={14}/><span className="hidden sm:inline">Delete</span></button>}</div>
        {(creating || canEditSelected) ? <><label className="mt-5 block text-[10px] font-semibold uppercase tracking-[.12em] text-muted">Title<input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={180} className="field mt-2 text-sm font-semibold" placeholder="What are you investigating?"/></label>
        <label className="mt-4 block text-[10px] font-semibold uppercase tracking-[.12em] text-muted">Notes<textarea value={body} onChange={(event) => setBody(event.target.value)} maxLength={20000} rows={15} className="field mt-2 min-h-[320px] resize-y py-4 text-sm leading-7" placeholder="Record your observations, questions, and next steps…"/></label>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3"><span className="metadata text-[9px]">{body.length.toLocaleString()} / 20,000 characters</span><button type="button" onClick={save} disabled={pending || !dirty || !title.trim() || !body.trim()} className="primary-button w-auto px-4 text-xs"><Save size={15}/>{pending ? 'Saving…' : 'Save note'}</button></div></> : <div className="mt-5"><h3 className="font-display text-2xl text-primary">{selected?.title}</h3><p className="mt-5 whitespace-pre-line text-sm leading-7 text-secondary">{selected?.body}</p></div>}
        {error && <p role="alert" className="mt-3 text-xs text-danger-text">{error instanceof ApiError ? error.message : 'The note could not be saved'}</p>}
      </article> : <div className="card grid min-h-96 place-items-center p-8 text-center"><div><FilePenLine className="mx-auto text-muted"/><h3 className="empty-title mt-4">Select a note</h3><p className="mt-2 text-sm text-muted">Choose one of your private notes to read.</p></div></div>}
    </div>}
  </section>
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
