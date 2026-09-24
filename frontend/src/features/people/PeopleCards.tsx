import { FileText, Share2 } from 'lucide-react'
import type { CasePerson } from '../../types'
import { categoryConfig } from './config'
import { Avatar } from './PeopleList'

export function PeopleCards({ people, onSelect }: { people: CasePerson[]; onSelect: (id: string) => void }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">{people.map((person) => <button type="button" key={person.id} onClick={() => onSelect(person.id)} className={`rounded-xl border border-subtle border-t-2 ${categoryConfig[person.category].ring} bg-surface/90 p-5 text-left shadow-card transition duration-200 hover:-translate-y-0.5 hover:border-strong`}><div className="flex items-start gap-4"><Avatar person={person} large/><div className="min-w-0"><h3 className="font-display text-xl font-semibold leading-tight text-primary">{person.name}</h3><p className="mt-1 text-xs font-medium" style={{ color: categoryConfig[person.category].color }}>{person.role}</p><span className="metadata mt-2 block text-[10px] uppercase">{categoryConfig[person.category].label}</span></div></div><p className="mt-4 line-clamp-3 min-h-[60px] text-xs leading-5 text-secondary">{person.summary || 'No case summary has been added for this person.'}</p><div className="mt-4 flex gap-2 border-t border-subtle pt-3"><span className="metadata inline-flex items-center gap-1"><Share2 size={12}/>{person.connection_count} connections</span><span className="metadata inline-flex items-center gap-1"><FileText size={12}/>{person.evidence_count} evidence</span></div></button>)}</div>
}
