import type { ReactNode } from 'react'
import { Brand } from './Brand'

export function AuthLayout({ eyebrow, title, description, children, footer, metal = false, signinBackground = false }: { eyebrow: string; title: string; description: string; children: ReactNode; footer: ReactNode; metal?: boolean; signinBackground?: boolean }) {
  return <main className="relative min-h-dvh overflow-hidden bg-background">
    <div className={`absolute inset-0 bg-background bg-cover bg-center ${signinBackground ? "bg-[url('/signin-background.png')]" : "bg-[url('/login-bkg.png')] md:bg-[url('/auth-horizontal-background.png')]"}`} aria-hidden="true" />
    <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(11,17,23,.2)_0%,rgba(11,17,23,.78)_52%,rgba(11,17,23,.98)_100%)] md:bg-[linear-gradient(180deg,rgba(11,17,23,.28)_0%,rgba(11,17,23,.48)_55%,rgba(11,17,23,.72)_100%)]" aria-hidden="true" />
    <div className="relative z-10 mx-auto flex min-h-dvh max-w-7xl flex-col px-5 py-6 lg:px-10">
      <Brand light />
      <div className="flex flex-1 items-end pb-7 pt-16 md:items-center md:justify-center md:py-10">
        <section className={`${metal ? 'auth-metal-card' : 'surface bg-surface/95'} w-full p-6 backdrop-blur-xl sm:mx-auto sm:max-w-md sm:p-9 lg:mx-0`}>
          <div className="editorial-rule mb-7" />
          <p className="eyebrow">{eyebrow}</p>
          <h1 className="page-title mt-3">{title}</h1>
          <p className="mt-4 text-[15px] leading-6 text-secondary">{description}</p>
          <div className="mt-8">{children}</div>
          <div className="mt-7 border-t border-subtle pt-5 text-center text-sm text-muted">{footer}</div>
        </section>
      </div>
      <p className="text-center text-[11px] font-medium uppercase tracking-[.14em] text-muted">People · Evidence · Places · Answers</p>
    </div>
  </main>
}
