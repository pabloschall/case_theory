import { useInfiniteQuery } from '@tanstack/react-query'
import { Check, ChevronDown, Paperclip } from 'lucide-react'
import { api } from '../../services/api'

export function EvidencePicker({ caseId, selected, onToggle }: { caseId: string; selected: string[]; onToggle: (id: string) => void }) {
  const query = useInfiniteQuery({
    queryKey: ['case', caseId, 'evidence'],
    queryFn: ({ pageParam }) => api.evidence(caseId, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
  })
  const items = (query.data?.pages.flatMap((page) => page.items) ?? []).filter((item) => item.processing_status === 'available')
  return <div className="rounded-xl border border-subtle bg-background/35 p-3"><p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.12em] text-muted"><Paperclip size={13}/> Attach case evidence</p>{items.length ? <div className="mt-3 max-h-52 space-y-2 overflow-y-auto">{items.map((item) => { const active = selected.includes(item.id); return <button type="button" key={item.id} onClick={() => onToggle(item.id)} className={`flex min-h-11 w-full items-center gap-3 rounded-lg border px-3 text-left text-xs transition duration-200 ${active ? 'border-accent/70 bg-accent-muted text-primary' : 'border-default text-muted hover:border-strong'}`}><span className={`grid size-5 shrink-0 place-items-center rounded-md border ${active ? 'border-accent bg-accent text-background' : 'border-default'}`}>{active && <Check size={13}/>}</span><span className="truncate">{item.title}</span></button> })}{query.hasNextPage && <button type="button" onClick={() => query.fetchNextPage()} disabled={query.isFetchingNextPage} className="ghost-button w-full text-[10px]"><ChevronDown size={13}/>{query.isFetchingNextPage ? 'Loading…' : 'More evidence'}</button>}</div> : <p className="mt-3 text-xs text-muted">Add evidence in the Evidence tab first.</p>}</div>
}
