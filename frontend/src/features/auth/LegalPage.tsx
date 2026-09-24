import { ArrowLeft, Scale, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router'
import { Brand } from '../../components/Brand'
import { APP_NAME } from '../../config/brand'

const terms = [
  ['Use the platform responsibly', `Use ${APP_NAME} for lawful, good-faith research. Clearly distinguish sourced facts, personal notes, theories, disputed claims, and AI-assisted synthesis.`],
  ['Share only permitted material', 'Upload or link only material you own, are authorized to share, or may lawfully use. Do not upload illegal, exploitative, stolen, or malicious files.'],
  ['Protect people and investigations', 'Do not publish private addresses, phone numbers, email addresses, financial data, non-public medical information, or other sensitive personal information.'],
  ['Account responsibility', `You are responsible for activity through your account and for maintaining the security of your credentials. ${APP_NAME} may restrict or remove accounts and content that violate these terms.`],
]

const standards = [
  ['No harassment or threats', 'Do not harass, threaten, stalk, intimidate, or organize targeted abuse against any person.'],
  ['No doxxing', 'Do not share private personal information or precise sensitive locations. Respect requests involving safety and privacy.'],
  ['Avoid reckless accusations', 'Do not present a theory, rumor, or AI inference as a verified fact. Do not automatically label real people as suspects or guilty.'],
  ['Use sources honestly', 'Provide links and provenance where possible. Never fabricate sources, alter evidence deceptively, or hide material context.'],
  ['No prohibited material', 'Do not upload illegal content, malware, exploitative imagery, or content that you do not have the right to distribute. Report material that may violate these standards.'],
]

export function LegalPage({ kind }: { kind: 'terms' | 'standards' }) {
  const isTerms = kind === 'terms'
  const sections = isTerms ? terms : standards
  return <main className="min-h-dvh bg-paper px-4 py-8 text-primary sm:py-12"><div className="mx-auto max-w-3xl"><header className="flex items-center justify-between"><Brand/><Link to="/register" className="secondary-button min-h-10 px-3 text-xs"><ArrowLeft size={14}/>Registration</Link></header><article className="surface mt-8 p-6 sm:p-10"><div className="flex items-center gap-2 text-accent">{isTerms ? <Scale size={18}/> : <ShieldCheck size={18}/>}<p className="eyebrow">Effective September 22, 2026</p></div><h1 className="page-title mt-4">{isTerms ? 'Terms of Use' : 'Community Standards'}</h1><p className="mt-4 max-w-2xl text-sm leading-7 text-secondary">{isTerms ? `These terms establish the basic responsibilities for using ${APP_NAME} as a collaborative public-case research workspace.` : `${APP_NAME} depends on careful sourcing, respect for real people, and collaboration without harassment or reckless accusations.`}</p><div className="mt-8 space-y-6">{sections.map(([title, body]) => <section key={title} className="border-t border-subtle pt-5"><h2 className="section-title">{title}</h2><p className="mt-2 text-sm leading-7 text-secondary">{body}</p></section>)}</div><div className="mt-8 rounded-lg border border-accent/25 bg-accent-muted p-4 text-xs leading-6 text-secondary">By creating an account, you confirm that you are at least 18 years old and agree to the current Terms of Use and Community Standards.</div></article></div></main>
}
