import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, Ban, MessageCircle, Undo2 } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'
import { APP_NAME } from '../../config/brand'
import { queryClient } from '../../lib/query'
import { api } from '../../services/api'
import type { MemberProfile } from '../../types'
import { ReportButton } from '../moderation/ReportButton'

export function MemberProfilePage() {
  const { userId = '' } = useParams()
  const navigate = useNavigate()
  const profile = useQuery({ queryKey: ['member', userId], queryFn: () => api.memberProfile(userId), enabled: Boolean(userId) })
  const current = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const message = useMutation({ mutationFn: () => api.openConversation(userId), onSuccess: (item) => navigate(`/messages/${item.id}`) })
  const block = useMutation({ mutationFn: (blocked: boolean) => blocked ? api.unblockUser(userId) : api.blockUser(userId), onSuccess: (state) => { queryClient.setQueryData(['member', userId], (previous: MemberProfile | undefined) => previous ? { ...previous, is_blocked_by_me: state.is_blocked } : previous); void queryClient.invalidateQueries({ queryKey: ['blocked-users'] }); void queryClient.invalidateQueries({ queryKey: ['messages'] }) } })
  if (profile.isLoading) return <div className="grid min-h-[55vh] place-items-center"><p className="eyebrow animate-pulse">Opening member profile</p></div>
  if (!profile.data) return <div className="card p-8 text-center text-muted">Member profile could not be loaded.</div>
  const item = profile.data
  const initials = item.display_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  return <div className="mx-auto max-w-2xl"><button type="button" onClick={() => navigate(-1)} className="ghost-button px-0 text-xs"><ArrowLeft size={15}/> Back</button><div className="card mt-5 p-7 sm:p-9"><div className="flex items-center gap-5"><div className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-full border border-accent/35 bg-accent-muted font-display text-2xl text-accent">{item.avatar_url ? <img src={item.avatar_url} alt="" className="size-full object-cover"/> : initials}</div><div><p className="eyebrow">{APP_NAME} member</p><h1 className="page-title mt-2">{item.display_name}</h1><p className="metadata mt-1">@{item.username}</p></div></div><p className="mt-7 text-sm leading-6 text-secondary">{item.bio || `A member of the ${APP_NAME} investigation community.`}</p>{current.data?.id !== item.id && <div className="mt-7 flex flex-wrap gap-3">{!item.is_blocked_by_me && <button type="button" onClick={() => message.mutate()} disabled={message.isPending} className="primary-button w-fit"><MessageCircle size={17}/>{message.isPending ? 'Opening…' : 'Send message'}</button>}<button type="button" onClick={() => block.mutate(item.is_blocked_by_me)} disabled={block.isPending} className={item.is_blocked_by_me ? 'secondary-button w-fit' : 'danger-button w-fit'}>{item.is_blocked_by_me ? <Undo2 size={16}/> : <Ban size={16}/>} {block.isPending ? 'Updating…' : item.is_blocked_by_me ? 'Unblock user' : 'Block user'}</button><ReportButton resourceType="user" resourceId={item.id} label="Report user"/></div>}{item.is_blocked_by_me && <p className="mt-4 text-xs text-muted">This member cannot start or continue a private conversation with you.</p>}{message.error && <p className="mt-4 text-xs text-danger">{message.error instanceof Error ? message.error.message : 'Conversation could not be opened.'}</p>}</div></div>
}
