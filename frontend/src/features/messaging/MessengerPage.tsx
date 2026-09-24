import { useInfiniteQuery, useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, ChevronDown, ChevronUp, Download, File, Image, MessageCircle, Paperclip, Send, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { PageHeader, UpgradePanel } from '../../components/ui/Visual'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'
import type { DirectConversation, MessageAttachment } from '../../types'

export function MessengerPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const currentUser = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const canMessage = currentUser.data?.permissions.includes('messaging.use') ?? false
  const list = useInfiniteQuery({
    queryKey: ['messages', 'conversations'],
    queryFn: ({ pageParam }) => api.conversations(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: canMessage,
    refetchInterval: 5000,
  })
  const conversations = list.data?.pages.flatMap((page) => page.items) ?? []
  const selected = useInfiniteQuery({
    queryKey: ['messages', 'conversation', conversationId],
    queryFn: ({ pageParam }) => api.conversation(conversationId!, pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.next_cursor ?? undefined,
    enabled: canMessage && Boolean(conversationId),
    refetchInterval: 3000,
  })
  const selectedPages = selected.data?.pages
  const latestPage = selectedPages?.[0]
  const messages = selectedPages
    ? Array.from(new Map(selectedPages.slice().reverse().flatMap((page) => page.messages).map((message) => [message.id, message])).values())
    : []
  const item = latestPage ? { ...latestPage, messages } : undefined
  if (currentUser.isLoading) return <div className="grid min-h-[50vh] place-items-center"><p className="eyebrow animate-pulse">Checking access</p></div>
  if (!canMessage) return <div><PageHeader eyebrow="Private collaboration" title="Messenger" description="Exchange focused notes, photos, and files with another investigator."/><div className="mt-7"><UpgradePanel title="Messenger is locked" description="Private messaging, photos, and file attachments are available to Investigator members."/></div></div>
  return <div><PageHeader eyebrow="Private collaboration" title="Messenger" description="Exchange focused notes, photos, and files with another investigator."/><div className="mt-7 grid min-h-[60vh] overflow-hidden rounded-xl border border-subtle bg-surface lg:grid-cols-[320px_1fr]"><aside className={`${conversationId ? 'hidden lg:block' : 'block'} border-r border-subtle`}><div className="border-b border-subtle p-4"><p className="eyebrow">Conversations</p></div>{list.isLoading && <p className="p-5 text-xs text-muted">Loading messages…</p>}{!list.isLoading && conversations.length === 0 && <div className="p-7 text-center"><MessageCircle className="mx-auto text-muted"/><p className="mt-3 font-display text-xl">No messages yet</p><p className="mt-2 text-xs leading-5 text-muted">Open a contributor’s profile to begin a conversation.</p></div>}{conversations.map((conversation) => <button type="button" key={conversation.id} onClick={() => navigate(`/messages/${conversation.id}`)} className={`flex w-full gap-3 border-b border-subtle p-4 text-left transition hover:bg-white/[.03] ${conversationId === conversation.id ? 'bg-accent-muted' : ''}`}><Avatar name={conversation.other_user.display_name}/><span className="min-w-0"><strong className="block truncate text-sm text-primary">{conversation.other_user.display_name}</strong><span className="mt-1 block truncate text-xs text-muted">{conversation.last_message || 'Conversation opened'}</span></span></button>)}{list.hasNextPage && <div className="p-3"><button type="button" onClick={() => list.fetchNextPage()} disabled={list.isFetchingNextPage} className="ghost-button w-full text-[10px]"><ChevronDown size={14}/>{list.isFetchingNextPage ? 'Loading…' : 'More conversations'}</button></div>}</aside><main className={`${conversationId ? 'flex' : 'hidden lg:flex'} min-w-0 flex-col`}>{item ? <Conversation item={item} loadEarlier={() => selected.fetchNextPage()} hasEarlier={selected.hasNextPage} loadingEarlier={selected.isFetchingNextPage}/> : <div className="grid flex-1 place-items-center p-8 text-center"><div><MessageCircle className="mx-auto text-muted"/><p className="mt-4 font-display text-2xl text-primary">Select a conversation</p><p className="mt-2 text-sm text-muted">Messages and private attachments will appear here.</p></div></div>}</main></div></div>
}

function Conversation({ item, loadEarlier, hasEarlier, loadingEarlier }: { item: DirectConversation; loadEarlier: () => void; hasEarlier: boolean; loadingEarlier: boolean }) {
  const [body, setBody] = useState('')
  const [attachments, setAttachments] = useState<MessageAttachment[]>([])
  const [uploadError, setUploadError] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const current = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const upload = useMutation({ mutationFn: async (file: globalThis.File) => { const ticket = await api.requestMessageAttachment(item.id, { filename: file.name, content_type: file.type || 'application/octet-stream', file_size: file.size }); const response = await fetch(ticket.upload_url, { method: ticket.upload_method, headers: ticket.upload_headers, body: file }); if (!response.ok) throw new Error('Storage rejected the upload'); return api.completeMessageAttachment(item.id, ticket.attachment.id) }, onSuccess: (attachment) => setAttachments((items) => [...items, attachment]), onError: (error) => setUploadError(error instanceof Error ? error.message : 'File upload failed') })
  const send = useMutation({ mutationFn: () => api.sendDirectMessage(item.id, { body, attachment_ids: attachments.map((value) => value.id) }), onSuccess: async () => { setBody(''); setAttachments([]); await Promise.all([queryClient.invalidateQueries({ queryKey: ['messages', 'conversation', item.id] }), queryClient.invalidateQueries({ queryKey: ['messages', 'conversations'] })]) } })
  useEffect(() => { setBody(''); setAttachments([]); setUploadError('') }, [item.id])
  const chooseFiles = (files: FileList | null) => { if (!files) return; setUploadError(''); Array.from(files).slice(0, 10 - attachments.length).forEach((file) => upload.mutate(file)); if (input.current) input.current.value = '' }
  return <><header className="flex items-center gap-3 border-b border-subtle p-4"><Link to="/messages" className="ghost-button size-10 p-0 lg:hidden"><ArrowLeft size={17}/></Link><Avatar name={item.other_user.display_name}/><div><Link to={`/users/${item.other_user.id}`} className="text-sm font-semibold text-primary hover:text-accent">{item.other_user.display_name}</Link><p className="text-[10px] text-muted">@{item.other_user.username}</p></div></header><div className="flex-1 space-y-4 overflow-y-auto p-4 sm:p-6">{hasEarlier && <div className="flex justify-center"><button type="button" onClick={loadEarlier} disabled={loadingEarlier} className="ghost-button text-[10px]"><ChevronUp size={14}/>{loadingEarlier ? 'Loading messages…' : 'Load earlier messages'}</button></div>}{item.messages.length === 0 && <p className="py-12 text-center font-display text-xl text-muted">Begin with a focused note, photo, or file.</p>}{item.messages.map((message) => { const mine = message.sender.id === current.data?.id; return <article key={message.id} className={`max-w-[88%] rounded-xl border p-4 ${mine ? 'ml-auto border-accent/25 bg-accent-muted' : 'border-subtle bg-tertiary'}`}><Link to={`/users/${message.sender.id}`} className="text-[10px] font-semibold text-accent">{message.sender.display_name}</Link>{message.body && <p className="mt-2 whitespace-pre-line text-sm leading-6 text-primary">{message.body}</p>}{message.attachments.length > 0 && <div className="mt-3 space-y-2">{message.attachments.map((attachment) => <AttachmentButton key={attachment.id} conversationId={item.id} attachment={attachment}/>)}</div>}<time className="mt-2 block text-[9px] text-muted">{new Date(message.created_at).toLocaleString()}</time></article>})}</div><div className="border-t border-subtle p-4">{attachments.length > 0 && <div className="mb-3 flex flex-wrap gap-2">{attachments.map((attachment) => <span key={attachment.id} className="inline-flex items-center gap-2 rounded-md border border-blue/25 bg-blue-muted px-3 py-2 text-[10px] text-blue"><File size={13}/><span className="max-w-40 truncate">{attachment.original_filename}</span><button type="button" onClick={() => setAttachments((items) => items.filter((value) => value.id !== attachment.id))} aria-label={`Remove ${attachment.original_filename}`}><X size={12}/></button></span>)}</div>}<input ref={input} type="file" multiple className="sr-only" accept="image/*,video/*,audio/*,.pdf,.txt,.csv,.docx,.heic,.heif,.mov" onChange={(event) => chooseFiles(event.target.files)}/><div className="flex items-end gap-2"><button type="button" onClick={() => input.current?.click()} disabled={upload.isPending || attachments.length >= 10} className={`secondary-button size-11 shrink-0 p-0 ${attachments.length ? 'border-accent text-accent' : ''}`} aria-label="Attach photo or file"><Paperclip size={17}/></button><textarea value={body} onChange={(event) => setBody(event.target.value)} className="field min-h-11 max-h-32 resize-y py-3" placeholder={`Message ${item.other_user.display_name}`}/><button type="button" onClick={() => send.mutate()} disabled={send.isPending || upload.isPending || (!body.trim() && attachments.length === 0)} className="primary-button size-11 shrink-0 p-0" aria-label="Send message"><Send size={17}/></button></div>{upload.isPending && <p className="mt-2 text-[10px] text-accent">Uploading file securely…</p>}{uploadError && <p className="mt-2 text-xs text-danger">{uploadError}</p>}{send.error && <p className="mt-2 text-xs text-danger">{send.error instanceof ApiError ? send.error.message : 'Message could not be sent.'}</p>}<p className="mt-2 text-[10px] text-muted">On iPhone, choose Photo Library, Take Photo or Video, or Browse. Maximum 25 MB per file.</p></div></>
}

function AttachmentButton({ conversationId, attachment }: { conversationId: string; attachment: MessageAttachment }) { const open = async () => { const { url } = await api.messageAttachmentUrl(conversationId, attachment.id); window.open(url, '_blank', 'noopener,noreferrer') }; const Icon = attachment.mime_type.startsWith('image/') ? Image : File; return <button type="button" onClick={open} className="flex w-full items-center gap-2 rounded-lg border border-blue/25 bg-blue-muted p-3 text-left text-xs text-blue"><Icon size={15}/><span className="min-w-0 flex-1 truncate font-semibold">{attachment.original_filename}</span><Download size={14}/></button> }
function Avatar({ name }: { name: string }) { return <span className="grid size-10 shrink-0 place-items-center rounded-full border border-default bg-elevated text-xs font-bold text-accent">{name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()}</span> }
