import { useMutation } from '@tanstack/react-query'
import { Copy, Mail, MessageSquareText, UserPlus, X } from 'lucide-react'
import { useState } from 'react'
import { APP_NAME } from '../../config/brand'
import { ApiError, api } from '../../services/api'

export function InviteCollaborators({ caseId }: { caseId: string }) {
  const [open, setOpen] = useState(false)
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [copied, setCopied] = useState(false)
  const invitation = useMutation({ mutationFn: () => api.createCaseInvitation(caseId) })
  const close = () => { setOpen(false); setCopied(false) }
  const smsHref = invitation.data
    ? `sms:${phone.trim()}?body=${encodeURIComponent(invitation.data.message)}`
    : '#'
  const emailHref = invitation.data
    ? `mailto:${email.trim()}?subject=${encodeURIComponent(`Collaborate on ${invitation.data.case_title} in ${APP_NAME}`)}&body=${encodeURIComponent(invitation.data.message)}`
    : '#'
  const copy = async () => {
    if (!invitation.data) return
    await navigator.clipboard.writeText(invitation.data.invite_url)
    setCopied(true)
  }
  return <>
    <button type="button" className="secondary-button w-fit border-accent/45 text-xs text-accent" onClick={() => setOpen(true)}><UserPlus size={15}/> Invite person</button>
    {open && <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center sm:p-6" role="dialog" aria-modal="true" aria-label="Invite collaborators">
      <section className="max-h-[92dvh] w-full max-w-lg overflow-y-auto rounded-t-2xl border border-default bg-elevated p-5 shadow-2xl sm:rounded-2xl sm:p-7">
        <div className="flex items-start justify-between gap-4"><div><p className="eyebrow text-accent">Case collaboration</p><h2 className="section-title mt-2">Invite a friend</h2><p className="mt-2 text-sm leading-6 text-secondary">Create a private invitation link, then send it with your phone’s messaging or email app.</p></div><button type="button" onClick={close} className="ghost-button size-10 shrink-0 p-0" aria-label="Close"><X size={18}/></button></div>
        {!invitation.data && <><div className="info-panel mt-6"><p className="text-xs leading-5 text-secondary">The link can be accepted once and expires after 7 days. The recipient will sign in or create an account before joining.</p></div>{invitation.error && <p role="alert" className="error-banner mt-4">{invitation.error instanceof ApiError ? invitation.error.message : 'The invitation could not be created.'}</p>}<button type="button" disabled={invitation.isPending} onClick={() => invitation.mutate()} className="primary-button mt-6"><UserPlus size={16}/>{invitation.isPending ? 'Creating invitation…' : 'Create invitation link'}</button></>}
        {invitation.data && <div className="mt-6 space-y-5"><div className="rounded-lg border border-accent/25 bg-accent-muted p-4"><p className="text-sm font-semibold text-primary">Invitation ready</p><p className="mt-2 text-xs leading-5 text-secondary">{invitation.data.message}</p><p className="metadata mt-3 text-[10px]">Expires {new Date(invitation.data.expires_at).toLocaleDateString()}</p></div><label className="block text-xs font-semibold text-primary">Phone number <span className="font-normal text-muted">Optional</span><input value={phone} onChange={(event) => setPhone(event.target.value)} className="field mt-2" inputMode="tel" autoComplete="tel" placeholder="Select a contact in Messages instead"/></label><a href={smsHref} className="primary-button"><MessageSquareText size={17}/> Open text message</a><div className="border-t border-subtle pt-5"><label className="block text-xs font-semibold text-primary">Email address <span className="font-normal text-muted">Optional</span><input value={email} onChange={(event) => setEmail(event.target.value)} className="field mt-2" type="email" inputMode="email" autoComplete="email" placeholder="Select a recipient in Mail instead"/></label><a href={emailHref} className="secondary-button mt-3"><Mail size={17}/> Open email</a></div><button type="button" onClick={copy} className="ghost-button w-full text-xs text-secondary"><Copy size={15}/>{copied ? 'Link copied' : 'Copy invitation link'}</button><p className="text-[10px] leading-4 text-muted">Phone numbers and email addresses stay on this device and are not sent to {APP_NAME}.</p></div>}
      </section>
    </div>}
  </>
}
