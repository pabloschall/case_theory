import { useQuery } from '@tanstack/react-query'
import { Check, UserRound } from 'lucide-react'
import { api } from '../../services/api'

export function PersonPicker({ caseId, selected, onToggle }: { caseId: string; selected: string[]; onToggle: (id: string) => void }) {
  const query = useQuery({ queryKey: ['case', caseId, 'people'], queryFn: () => api.people(caseId) })
  const people = query.data ?? []
  return <div className="rounded-xl border border-subtle bg-background/35 p-3"><p className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[.12em] text-muted"><UserRound size={13}/> Link people or organizations</p>{people.length ? <div className="mt-3 max-h-52 space-y-2 overflow-y-auto">{people.map((person) => { const active = selected.includes(person.id); return <button type="button" key={person.id} onClick={() => onToggle(person.id)} className={`flex min-h-11 w-full items-center gap-3 rounded-lg border px-3 text-left text-xs transition duration-200 ${active ? 'border-accent/70 bg-accent-muted text-primary' : 'border-default text-muted hover:border-strong'}`}><span className={`grid size-5 shrink-0 place-items-center rounded-md border ${active ? 'border-accent bg-accent text-background' : 'border-default'}`}>{active && <Check size={13}/>}</span><span className="min-w-0"><span className="block truncate font-semibold text-primary">{person.name}</span><span className="block truncate text-[10px] text-muted">{person.role}</span></span></button> })}</div> : <p className="mt-3 text-xs text-muted">Add a person in the People tab first. People do not need to be linked to anything.</p>}</div>
}

export function LinkedPeople({ people }: { people: { id: string; name: string; role: string }[] }) {
  if (!people.length) return null
  return <div className="mt-3 flex flex-wrap gap-2">{people.map((person) => <span key={person.id} className="inline-flex items-center gap-1.5 rounded-md border border-accent/25 bg-accent-muted px-2.5 py-1 text-[10px] font-medium text-primary"><UserRound size={11}/>{person.name}<span className="text-muted">· {person.role}</span></span>)}</div>
}
