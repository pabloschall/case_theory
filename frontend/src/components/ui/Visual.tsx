import type { ReactNode } from 'react'
import { LockKeyhole, X, type LucideIcon } from 'lucide-react'
import { useState } from 'react'

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="eyebrow">{eyebrow}</p><h1 className="page-title mt-3">{title}</h1>{description && <p className="mt-4 max-w-2xl text-[15px] leading-7 text-secondary">{description}</p>}</div>{action}</header>
}

export function SectionHeader({ eyebrow, title, action }: { eyebrow: string; title: ReactNode; action?: ReactNode }) {
  return <div className="flex items-end justify-between gap-4"><div><p className="eyebrow">{eyebrow}</p><h2 className="section-title mt-2">{title}</h2></div>{action}</div>
}

export function EmptyState({ icon: Icon, title, children }: { icon: LucideIcon; title: string; children: ReactNode }) {
  return <div className="card grid min-h-56 place-items-center p-8 text-center"><div><Icon className="mx-auto text-muted"/><h3 className="empty-title mt-4">{title}</h3><p className="mx-auto mt-2 max-w-md text-sm leading-6 text-muted">{children}</p></div></div>
}

export function StatusBadge({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'ai' | 'info' | 'success' | 'warning' | 'danger' }) {
  const tones = { neutral: 'border-default text-secondary', ai: 'border-accent/35 bg-accent-muted text-accent', info: 'border-info/35 bg-blue-muted text-blue', success: 'border-success/35 text-success', warning: 'border-warning/35 text-warning', danger: 'border-danger/35 text-danger' }
  return <span className={`status-badge ${tones[tone]}`}>{children}</span>
}

export function BottomSheet({ children }: { children: ReactNode }) {
  return <section className="fixed inset-x-0 bottom-0 z-40 max-h-[85dvh] overflow-y-auto rounded-t-2xl border border-subtle bg-elevated p-5 shadow-card md:static md:rounded-xl">{children}</section>
}

export function LockedFeature({ message, children }: { message: string; children: ReactNode }) {
  return <div className="relative overflow-hidden rounded-xl"><div aria-hidden="true" className="pointer-events-none opacity-45">{children}</div><div className="absolute inset-0 grid place-items-center bg-background/75 p-5 text-center"><p className="text-sm font-semibold text-secondary">{message}</p></div></div>
}

export function UpgradeButton({ children, requiredTier = 2, description, className = 'secondary-button text-xs' }: { children: ReactNode; requiredTier?: 2 | 3; description: string; className?: string }) {
  const [open, setOpen] = useState(false)
  const plan = requiredTier === 3 ? 'Lead Investigator' : 'Investigator'
  return <>
    <button type="button" onClick={() => setOpen(true)} className={className}><LockKeyhole size={15}/>{children}</button>
    {open && <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/70 backdrop-blur-sm sm:items-center sm:p-6" role="dialog" aria-modal="true" aria-label={`${plan} plan required`} onClick={() => setOpen(false)}><section className="w-full max-w-md rounded-t-2xl border border-default bg-elevated p-6 shadow-2xl sm:rounded-2xl" onClick={(event) => event.stopPropagation()}><div className="flex items-start justify-between gap-4"><span className="grid size-11 place-items-center rounded-lg border border-accent/30 bg-accent-muted text-accent"><LockKeyhole size={20}/></span><button type="button" className="ghost-button size-10 p-0" aria-label="Close" onClick={() => setOpen(false)}><X size={18}/></button></div><p className="eyebrow mt-5 text-accent">Tier {requiredTier}</p><h2 className="section-title mt-2">Available to {plan}s</h2><p className="mt-3 text-sm leading-6 text-secondary">{description}</p><button type="button" className="primary-button mt-6 w-full" onClick={() => setOpen(false)}>Got it</button></section></div>}
  </>
}

export function UpgradePanel({ title, description, requiredTier = 2 }: { title: string; description: string; requiredTier?: 2 | 3 }) {
  return <div className="card grid min-h-64 place-items-center p-8 text-center"><div><span className="mx-auto grid size-12 place-items-center rounded-xl border border-accent/30 bg-accent-muted text-accent"><LockKeyhole size={22}/></span><h2 className="empty-title mt-5">{title}</h2><p className="mx-auto mt-3 max-w-md text-sm leading-6 text-secondary">{description}</p><p className="eyebrow mt-5 text-accent">Tier {requiredTier} required</p></div></div>
}
