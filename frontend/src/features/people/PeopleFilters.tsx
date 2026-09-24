import { UsersRound } from 'lucide-react'
import type { CasePerson, PersonCategory } from '../../types'
import { categoryConfig, categoryOrder } from './config'

export type PeopleFilter = 'all' | PersonCategory

export function PeopleFilters({ people, value, onChange, mobile = false }: { people: CasePerson[]; value: PeopleFilter; onChange: (value: PeopleFilter) => void; mobile?: boolean }) {
  const items: { value: PeopleFilter; label: string; count: number; dot?: string }[] = [
    { value: 'all', label: 'All People', count: people.length },
    ...categoryOrder.map((category) => ({ value: category, label: categoryConfig[category].label, count: people.filter((person) => person.category === category).length, dot: categoryConfig[category].dot })),
  ]
  if (mobile) return <div className="flex gap-2 overflow-x-auto pb-2">{items.map((item) => <button type="button" key={item.value} onClick={() => onChange(item.value)} className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-lg border px-3 text-[11px] font-semibold transition ${value === item.value ? 'border-accent/45 bg-accent-muted text-primary' : 'border-subtle bg-surface text-muted'}`}>{item.dot ? <span className={`size-2 rounded-full ${item.dot}`}/> : <UsersRound size={13} className="text-accent"/>}{item.label}<span className="text-[10px] text-muted">{item.count}</span></button>)}</div>
  return <aside className="overflow-hidden rounded-xl border border-subtle bg-surface/80 py-2 shadow-card">{items.map((item) => <button type="button" key={item.value} onClick={() => onChange(item.value)} className={`flex min-h-11 w-full items-center gap-2.5 border-l-2 px-4 text-left text-xs transition ${value === item.value ? 'border-l-accent bg-accent-muted text-primary' : 'border-l-transparent text-secondary hover:bg-white/[.025] hover:text-primary'}`}>{item.dot ? <span className={`size-2 rounded-full ${item.dot}`}/> : <UsersRound size={14} className="text-accent"/>}<span className="min-w-0 flex-1 truncate font-medium">{item.label}</span><span className="text-[10px] text-muted">{item.count}</span></button>)}</aside>
}
