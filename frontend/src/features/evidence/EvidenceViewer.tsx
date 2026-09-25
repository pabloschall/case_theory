import { ExternalLink, FileQuestion, LoaderCircle, X } from 'lucide-react'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { createPortal } from 'react-dom'
import { ApiError, api } from '../../services/api'
import type { Evidence } from '../../types'

type PreviewKind = 'image' | 'video' | 'audio' | 'pdf' | 'youtube' | 'web' | 'unsupported'

export function EvidenceViewer({ caseId, item, onClose }: { caseId: string; item: Evidence; onClose: () => void }) {
  const [resolvedUrl, setResolvedUrl] = useState<string | null>(item.source_url)
  const [loading, setLoading] = useState(!item.source_url)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const handleKeyDown = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [onClose])

  useEffect(() => {
    if (item.source_url) return
    let active = true
    setLoading(true)
    api.evidenceUrl(caseId, item.id)
      .then(({ url }) => { if (active) setResolvedUrl(url) })
      .catch((value: unknown) => { if (active) setError(value instanceof Error ? value : new Error('Evidence could not be opened')) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [caseId, item.id, item.source_url])

  const preview = useMemo(() => getPreview(item, resolvedUrl), [item, resolvedUrl])
  const originalLabel = item.source_url ? 'Open original source' : 'Open original file'

  return createPortal(
    <div className="fixed inset-0 z-[80] flex items-end justify-center bg-black/80 backdrop-blur-sm sm:items-center sm:p-5" role="dialog" aria-modal="true" aria-labelledby={`evidence-viewer-title-${item.id}`} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose() }}>
      <section className="flex h-[96dvh] w-full min-w-0 flex-col overflow-hidden rounded-t-2xl border border-default bg-elevated shadow-2xl sm:h-[min(88dvh,850px)] sm:max-w-6xl sm:rounded-2xl">
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-subtle px-4 py-4 sm:px-6">
          <div className="min-w-0"><p className="eyebrow">Evidence viewer</p><h2 id={`evidence-viewer-title-${item.id}`} className="section-title mt-1 truncate">{item.title}</h2></div>
          <div className="flex shrink-0 items-center gap-2">
            {resolvedUrl && <a href={resolvedUrl} target="_blank" rel="noreferrer" className="secondary-button min-h-10 w-auto px-3 text-[11px]"><ExternalLink size={14}/><span className="hidden sm:inline">{originalLabel}</span><span className="sm:hidden">Original</span></a>}
            <button type="button" autoFocus onClick={onClose} className="ghost-button size-10 p-0" aria-label="Close evidence viewer"><X size={19}/></button>
          </div>
        </header>

        <div className="min-h-0 flex-1 bg-background">
          {loading ? <ViewerMessage icon={<LoaderCircle className="animate-spin text-accent"/>} title="Preparing evidence" body="Creating secure access to the original file…"/> : error ? <ViewerMessage icon={<FileQuestion className="text-danger"/>} title="Evidence unavailable" body={error instanceof ApiError ? error.message : 'This evidence could not be loaded.'}/> : resolvedUrl ? <EvidencePreview kind={preview.kind} url={preview.url} title={item.title}/> : <ViewerMessage icon={<FileQuestion className="text-muted"/>} title="No preview available" body="This record does not contain a viewable file or source."/>}
        </div>

        <footer className="shrink-0 border-t border-subtle bg-surface/95 px-4 py-4 sm:px-6">
          <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
            <div className="min-w-0"><p className="text-xs font-semibold text-primary">{item.original_filename || host(item.source_url)}</p>{item.description && <p className="mt-1 max-w-3xl break-words text-xs leading-5 text-secondary">{item.description}</p>}</div>
            <div className="flex flex-wrap gap-2"><span className="status-badge">{item.evidence_type.replaceAll('_', ' ')}</span><span className="status-badge">{item.verification_status.replaceAll('_', ' ')}</span>{item.ai_generated && <span className="ai-label">AI suggested</span>}</div>
          </div>
          {preview.kind === 'web' && <p className="mt-3 text-[10px] leading-4 text-muted">External publishers control how their pages open. Case Theory links to the original page without copying or altering its content.</p>}
        </footer>
      </section>
    </div>,
    document.body,
  )
}

function EvidencePreview({ kind, url, title }: { kind: PreviewKind; url: string; title: string }) {
  if (kind === 'image') return <div className="grid size-full place-items-center overflow-auto p-3 sm:p-6"><img src={url} alt={title} className="max-h-full max-w-full object-contain"/></div>
  if (kind === 'video') return <div className="grid size-full place-items-center p-3 sm:p-6"><video src={url} controls playsInline className="max-h-full max-w-full"/></div>
  if (kind === 'audio') return <div className="grid size-full place-items-center p-6"><div className="card w-full max-w-xl p-6 text-center"><p className="font-display text-2xl text-primary">Audio evidence</p><audio src={url} controls className="mt-6 w-full"/></div></div>
  if (kind === 'unsupported') return <ViewerMessage icon={<FileQuestion className="text-blue"/>} title="Preview not supported" body="This file type cannot be displayed safely in the browser. Open the original file to inspect it."/>
  if (kind === 'web') return <ViewerMessage icon={<ExternalLink className="text-blue"/>} title="View this source on its website" body="This publisher does not provide a dependable in-app preview." action={<a href={url} target="_blank" rel="noreferrer" className="primary-button mt-5 w-fit"><ExternalLink size={15}/> Open original source</a>}/>
  return <iframe src={url} title={`${title} evidence preview`} className="size-full border-0 bg-white" referrerPolicy="strict-origin-when-cross-origin" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" allowFullScreen/>
}

function ViewerMessage({ icon, title, body, action }: { icon: ReactNode; title: string; body: string; action?: ReactNode }) {
  return <div className="grid size-full place-items-center p-8 text-center"><div className="flex flex-col items-center">{icon}<h3 className="empty-title mt-4">{title}</h3><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{body}</p>{action}</div></div>
}

function getPreview(item: Evidence, value: string | null): { kind: PreviewKind; url: string } {
  if (!value) return { kind: 'unsupported', url: '' }
  const youtube = youtubeEmbed(value)
  if (youtube) return { kind: 'youtube', url: youtube }
  const mime = item.mime_type?.toLowerCase() ?? ''
  const path = safePath(value).toLowerCase()
  if (mime.startsWith('image/') || /\.(png|jpe?g|webp|gif|avif)$/.test(path)) return { kind: 'image', url: value }
  if (mime.startsWith('video/') || /\.(mp4|webm|mov|m4v)$/.test(path)) return { kind: 'video', url: value }
  if (mime.startsWith('audio/') || /\.(mp3|wav|ogg|m4a|aac)$/.test(path)) return { kind: 'audio', url: value }
  if (mime === 'application/pdf' || path.endsWith('.pdf')) return { kind: 'pdf', url: value }
  if (item.source_url) return { kind: 'web', url: value }
  return { kind: 'unsupported', url: value }
}

function youtubeEmbed(value: string): string | null {
  try {
    const url = new URL(value)
    const hostname = url.hostname.replace(/^www\./, '')
    let id: string | null = null
    if (hostname === 'youtu.be') id = url.pathname.split('/').filter(Boolean)[0] ?? null
    if (hostname === 'youtube.com' || hostname === 'm.youtube.com') id = url.pathname === '/watch' ? url.searchParams.get('v') : url.pathname.match(/^\/(?:embed|shorts)\/([^/]+)/)?.[1] ?? null
    return id && /^[\w-]{6,20}$/.test(id) ? `https://www.youtube-nocookie.com/embed/${id}` : null
  } catch { return null }
}

function safePath(value: string) { try { return new URL(value).pathname } catch { return '' } }
function host(value: string | null) { try { return value ? new URL(value).hostname : 'Stored evidence file' } catch { return 'External source' } }
