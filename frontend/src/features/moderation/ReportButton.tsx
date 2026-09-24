import { useMutation } from '@tanstack/react-query'
import { Flag, ShieldAlert, X } from 'lucide-react'
import { useState } from 'react'
import { ApiError, api } from '../../services/api'
import type { ReportReason, ReportResourceType } from '../../types'

const reasons: { value: ReportReason; label: string }[] = [
  { value: 'harassment', label: 'Harassment or threats' },
  { value: 'hate_speech', label: 'Hate speech or racist remark' },
  { value: 'doxxing', label: 'Private information or doxxing' },
  { value: 'illegal_material', label: 'Illegal or dangerous material' },
  { value: 'misinformation', label: 'Misleading or fabricated information' },
  { value: 'spam', label: 'Spam or manipulation' },
  { value: 'other', label: 'Other concern' },
]

export function ReportButton({ resourceType, resourceId, label = 'Report', onReported }: { resourceType: ReportResourceType; resourceId: string; label?: string; onReported?: () => void }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState<ReportReason>('harassment')
  const [details, setDetails] = useState('')
  const report = useMutation({
    mutationFn: () => api.createReport({ resource_type: resourceType, resource_id: resourceId, reason_code: reason, details }),
    onSuccess: () => { onReported?.() },
  })

  return <>
    <button type="button" onClick={() => { report.reset(); setOpen(true) }} className="ghost-button min-h-8 w-auto px-2 text-[10px] text-muted"><Flag size={13}/>{label}</button>
    {open && <div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/75 backdrop-blur-sm sm:items-center sm:p-5" role="dialog" aria-modal="true" aria-label="Report content" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false) }}>
      <section className="w-full max-w-lg rounded-t-2xl border border-default bg-elevated p-5 shadow-2xl sm:rounded-2xl sm:p-6">
        {report.isSuccess ? <div className="py-5 text-center"><ShieldAlert className="mx-auto text-accent"/><h2 className="section-title mt-4">Report sent for review</h2><p className="mt-3 text-sm leading-6 text-secondary">A moderator will review the context and decide whether to hide the content or restrict the account.</p><button type="button" onClick={() => setOpen(false)} className="primary-button mt-6 w-full">Done</button></div> : <>
          <div className="flex items-start justify-between gap-4"><div><p className="eyebrow">Community safety</p><h2 className="section-title mt-2">Report for review</h2></div><button type="button" onClick={() => setOpen(false)} className="ghost-button size-10 p-0" aria-label="Close report form"><X size={18}/></button></div>
          <p className="mt-3 text-xs leading-5 text-muted">Reports are reviewed with context. Filing a report does not automatically determine that a violation occurred.</p>
          <label className="mt-5 block text-xs font-semibold text-primary">Reason<select value={reason} onChange={(event) => setReason(event.target.value as ReportReason)} className="field mt-2">{reasons.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label className="mt-4 block text-xs font-semibold text-primary">What happened?<textarea value={details} onChange={(event) => setDetails(event.target.value)} maxLength={3000} rows={5} className="field mt-2 resize-y py-3" placeholder="Describe the specific content or behavior and why it should be reviewed."/></label>
          <div className="mt-2 text-right text-[9px] text-muted">{details.length}/3000</div>
          {report.error && <p role="alert" className="mt-3 text-xs text-danger-text">{report.error instanceof ApiError ? report.error.message : 'The report could not be submitted'}</p>}
          <button type="button" onClick={() => report.mutate()} disabled={report.isPending || details.trim().length < 10} className="danger-button mt-5 w-full"><Flag size={15}/>{report.isPending ? 'Sending…' : 'Submit report'}</button>
        </>}
      </section>
    </div>}
  </>
}
