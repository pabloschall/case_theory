import { useMutation } from '@tanstack/react-query'
import { ArrowRight, Bookmark, BookmarkCheck, CalendarDays, LockKeyhole, MessageSquare } from 'lucide-react'
import { Link } from 'react-router'
import { queryClient } from '../../lib/query'
import { api } from '../../services/api'
import type { CaseListItem } from '../../types'

const dateFormatter = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

export function CaseCard({ item, showFollow = true }: { item: CaseListItem; showFollow?: boolean }) {
  const followMutation = useMutation({
    mutationFn: () => item.is_following ? api.unfollowCase(item.id) : api.followCase(item.id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['cases'] })
      await queryClient.invalidateQueries({ queryKey: ['case', item.id] })
    },
  })

  return <article className="card group overflow-hidden transition duration-200 hover:-translate-y-0.5 hover:border-strong">
    <Link to={`/cases/${item.id}`} className="block">
      <div className="relative">
      <img src={item.cover_image_url || '/case-banner.png'} alt="Symbolic editorial case banner" className="h-36 w-full object-cover"/>
      <div className="absolute inset-0 bg-gradient-to-t from-background/80 to-transparent"/>
      {item.privacy === 'private' && <span className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-md border border-default bg-background/80 px-2 py-1 text-[9px] font-semibold uppercase tracking-[.12em] text-primary"><LockKeyhole size={11}/> Private</span>}
      </div>
      <div className="p-5 pb-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-[10px] font-semibold uppercase tracking-[.14em] text-accent">{[item.year, item.ai_research_status.replaceAll('_', ' ')].filter(Boolean).join(' · ')}</span>
          <ArrowRight className="text-muted transition-colors group-hover:text-accent" size={16}/>
        </div>
        <h3 className="case-title mt-3 text-2xl">{item.title}</h3>
        {item.location && <p className="metadata mt-2">{item.location}</p>}
      </div>
    </Link>
    <div className="mx-5 flex flex-wrap items-center justify-between gap-3 border-t border-subtle py-3 text-[11px] text-muted">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <span className="inline-flex items-center gap-1.5"><MessageSquare size={13}/>{item.discussion_count} {item.discussion_count === 1 ? 'discussion post' : 'discussion posts'}</span>
        <span className="inline-flex items-center gap-1.5"><CalendarDays size={13}/>Created {dateFormatter.format(new Date(item.created_at))}</span>
      </div>
      {showFollow && !item.is_owner && item.privacy === 'public' && <button type="button" onClick={() => followMutation.mutate()} disabled={followMutation.isPending} className={`ghost-button min-h-9 px-2 text-[11px] ${item.is_following ? 'text-accent' : 'text-secondary'}`}>{item.is_following ? <BookmarkCheck size={14}/> : <Bookmark size={14}/>} {followMutation.isPending ? 'Updating…' : item.is_following ? 'Following' : 'Follow'}</button>}
    </div>
  </article>
}
