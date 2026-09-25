import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, Calendar, Check, ExternalLink, FileText, Link2, MapPin, Network, NotebookPen, Pencil, Plus, Trash2, UserRound, X } from 'lucide-react'
import { useState } from 'react'
import { queryClient } from '../../lib/query'
import { api } from '../../services/api'
import type { CasePerson, PersonRelationship } from '../../types'
import { EvidenceCard } from '../evidence/EvidenceCard'
import { EvidencePicker } from '../evidence/EvidencePicker'
import { categoryConfig } from './config'
import { Avatar } from './PeopleList'

type DetailTab = 'overview' | 'connections' | 'evidence' | 'notes'

export function PersonDetailsPanel({ caseId, person, people, relationships, inspectedRelationship, onSelect, onClose, readOnly = false }: { caseId: string; person: CasePerson | null; people: CasePerson[]; relationships: PersonRelationship[]; inspectedRelationship: PersonRelationship | null; onSelect: (id: string) => void; onClose?: () => void; readOnly?: boolean }) {
  const [tab, setTab] = useState<DetailTab>('overview')
  if (!person) return <div className="grid min-h-72 place-items-center rounded-xl border border-subtle bg-surface/75 p-6 text-center"><div><Network className="mx-auto text-muted"/><p className="mt-4 font-display text-xl font-semibold text-primary">Select a person</p><p className="mt-2 text-xs leading-5 text-muted">Inspect their role, direct connections, supporting evidence, and investigator notes.</p></div></div>
  const direct = relationships.filter((item) => item.source_person_id === person.id || item.target_person_id === person.id)
  return <section className="overflow-hidden rounded-xl border border-subtle bg-surface/95 shadow-card">
    <div className="p-5"><div className="flex items-start gap-4"><Avatar person={person} large/><div className="min-w-0 flex-1"><h2 className="font-display text-2xl font-semibold leading-tight text-primary">{person.name}</h2><span className="mt-2 inline-flex rounded-md border px-2 py-1 text-[9px] font-bold uppercase tracking-[.1em]" style={{ color: categoryConfig[person.category].color, borderColor: categoryConfig[person.category].color, background: categoryConfig[person.category].muted }}>{person.role}</span>{person.ai_suggested && person.review_status === 'suggested' && <span className="ai-label ml-2">AI suggested</span>}</div>{onClose && <button type="button" onClick={onClose} className="ghost-button -mr-2 -mt-2 p-2" aria-label="Close person details"><X size={18}/></button>}</div>
      {inspectedRelationship && (inspectedRelationship.source_person_id === person.id || inspectedRelationship.target_person_id === person.id) && <RelationshipNotice relationship={inspectedRelationship} caseId={caseId} readOnly={readOnly}/>} 
    </div>
    <div className="flex overflow-x-auto border-y border-subtle px-3">{(['overview', 'connections', 'evidence', 'notes'] as DetailTab[]).map((value) => <button type="button" key={value} onClick={() => setTab(value)} className={`min-h-11 shrink-0 border-b-2 px-3 text-[10px] font-semibold capitalize transition ${tab === value ? 'border-accent text-accent' : 'border-transparent text-muted hover:text-primary'}`}>{value}{value === 'connections' ? ` ${direct.length}` : value === 'evidence' ? ` ${person.evidence_count}` : value === 'notes' ? ` ${person.notes_count}` : ''}</button>)}</div>
    <div className="p-5">{tab === 'overview' && <Overview person={person} onEvidence={() => setTab('evidence')}/>} {tab === 'connections' && <Connections person={person} people={people} relationships={direct} caseId={caseId} onSelect={onSelect} readOnly={readOnly}/>} {tab === 'evidence' && <PersonEvidence caseId={caseId} person={person} readOnly={readOnly}/>} {tab === 'notes' && <PersonNotes caseId={caseId} person={person} readOnly={readOnly}/>}</div>
  </section>
}

function Overview({ person, onEvidence }: { person: CasePerson; onEvidence: () => void }) {
  const fields = [
    { icon: UserRound, label: 'Full name', value: person.name },
    { icon: Calendar, label: 'Date of birth', value: person.date_of_birth ? new Intl.DateTimeFormat(undefined, { dateStyle: 'long' }).format(new Date(`${person.date_of_birth}T00:00:00`)) : 'Not documented' },
    { icon: MapPin, label: 'Place of birth', value: person.place_of_birth || 'Not documented' },
    { icon: Network, label: 'Role in case', value: person.role },
    { icon: Link2, label: 'Relationship to primary subject', value: person.relationship_to_primary || 'Not documented' },
  ]
  return <div><dl className="space-y-4">{fields.map(({ icon: Icon, label, value }) => <div key={label} className="flex gap-3"><Icon size={16} className="mt-0.5 shrink-0 text-muted"/><div><dt className="text-[10px] text-muted">{label}</dt><dd className="mt-1 text-xs leading-5 text-primary">{value}</dd></div></div>)}</dl><div className="mt-5 border-t border-subtle pt-4"><p className="text-[10px] text-muted">Case summary</p><p className="mt-2 text-xs leading-6 text-secondary">{person.summary || 'No sourced summary has been added yet.'}</p></div><button type="button" onClick={onEvidence} className="secondary-button mt-5 w-full border-accent/40 text-xs text-accent">View all evidence for this person <ArrowRight size={14}/></button></div>
}

function Connections({ person, people, relationships, caseId, onSelect, readOnly }: { person: CasePerson; people: CasePerson[]; relationships: PersonRelationship[]; caseId: string; onSelect: (id: string) => void; readOnly: boolean }) {
  const refresh = () => Promise.all([queryClient.invalidateQueries({ queryKey: ['case', caseId, 'relationships'] }), queryClient.invalidateQueries({ queryKey: ['case', caseId, 'people'] })])
  const review = useMutation({ mutationFn: ({ id, status }: { id: string; status: 'confirmed' | 'rejected' }) => api.reviewRelationship(caseId, id, status), onSuccess: refresh })
  if (!relationships.length) return <PanelEmpty icon={Network} text="No direct relationships are recorded."/>
  return <div className="space-y-2">{relationships.map((relationship) => { const otherId = relationship.source_person_id === person.id ? relationship.target_person_id : relationship.source_person_id; const other = people.find((item) => item.id === otherId); if (!other) return null; return <div key={relationship.id} className="rounded-lg border border-subtle bg-background/30 p-3"><button type="button" onClick={() => onSelect(other.id)} className="flex w-full items-center gap-3 text-left"><Avatar person={other}/><span className="min-w-0 flex-1"><strong className="block truncate text-xs text-primary">{other.name}</strong><span className="mt-0.5 block text-[10px] text-muted">{relationship.label}</span></span><ArrowRight size={14} className="text-muted"/></button>{relationship.description && <p className="mt-2 text-[10px] leading-5 text-secondary">{relationship.description}</p>}{relationship.source_url && <a href={relationship.source_url} target="_blank" rel="noreferrer" className="mt-2 inline-flex items-center gap-1 text-[10px] text-blue"><ExternalLink size={10}/>Supporting source</a>}{!readOnly && relationship.ai_suggested && relationship.review_status === 'suggested' && <div className="mt-3 flex gap-2 border-t border-subtle pt-2"><button type="button" onClick={() => review.mutate({ id: relationship.id, status: 'confirmed' })} className="ghost-button min-h-8 px-2 text-[9px] text-success"><Check size={12}/>Confirm</button><button type="button" onClick={() => review.mutate({ id: relationship.id, status: 'rejected' })} className="ghost-button min-h-8 px-2 text-[9px] text-danger"><X size={12}/>Reject</button></div>}</div> })}</div>
}

function PersonEvidence({ caseId, person, readOnly }: { caseId: string; person: CasePerson; readOnly: boolean }) {
  const [linking, setLinking] = useState(false)
  const [selected, setSelected] = useState<string[]>([])
  const query = useQuery({ queryKey: ['case', caseId, 'people', person.id, 'evidence'], queryFn: () => api.personEvidence(caseId, person.id) })
  const attach = useMutation({ mutationFn: () => api.attachPersonEvidence(caseId, person.id, selected[0]), onSuccess: async () => { setSelected([]); setLinking(false); await Promise.all([queryClient.invalidateQueries({ queryKey: ['case', caseId, 'people', person.id, 'evidence'] }), queryClient.invalidateQueries({ queryKey: ['case', caseId, 'people'] })]) } })
  if (query.isLoading) return <Loading/>
  if (query.isError) return <p className="error-banner">Evidence could not be loaded.</p>
  return <div>{!readOnly && <button type="button" onClick={() => { setLinking((value) => !value); setSelected([]) }} className="secondary-button mb-3 w-full text-xs"><Link2 size={14}/>{linking ? 'Cancel' : 'Link case evidence'}</button>}{linking && <div className="mb-4"><EvidencePicker caseId={caseId} selected={selected} onToggle={(id) => setSelected([id])}/><button type="button" disabled={!selected[0] || attach.isPending} onClick={() => attach.mutate()} className="primary-button mt-2 min-h-10 text-xs">{attach.isPending ? 'Linking…' : 'Link to person'}</button>{attach.error && <p role="alert" className="mt-2 text-xs text-danger">Evidence could not be linked.</p>}</div>}{query.data?.length ? <div className="space-y-2">{query.data.map((item) => <EvidenceCard key={item.id} caseId={caseId} item={item} compact/>)}</div> : !linking && <PanelEmpty icon={FileText} text="No evidence is linked to this person yet."/>}</div>
}

function PersonNotes({ caseId, person, readOnly }: { caseId: string; person: CasePerson; readOnly: boolean }) {
  const [body, setBody] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const queryKey = ['case', caseId, 'people', person.id, 'notes']
  const query = useQuery({ queryKey, queryFn: () => api.personNotes(caseId, person.id) })
  const refresh = async () => { setBody(''); setEditingId(null); await Promise.all([queryClient.invalidateQueries({ queryKey }), queryClient.invalidateQueries({ queryKey: ['case', caseId, 'people'] })]) }
  const save = useMutation({ mutationFn: () => editingId ? api.updatePersonNote(caseId, person.id, editingId, body) : api.createPersonNote(caseId, person.id, body), onSuccess: refresh })
  const remove = useMutation({ mutationFn: (id: string) => api.deletePersonNote(caseId, person.id, id), onSuccess: refresh })
  return <div>{!readOnly && <><textarea value={body} onChange={(event) => setBody(event.target.value)} className="field min-h-24 resize-y py-3" placeholder="Add an investigator note about this person…"/><div className="mt-2 flex gap-2"><button type="button" disabled={!body.trim() || save.isPending} onClick={() => save.mutate()} className="primary-button min-h-9 px-3 text-[10px]"><Plus size={13}/>{editingId ? 'Save note' : 'Add note'}</button>{editingId && <button type="button" onClick={() => { setEditingId(null); setBody('') }} className="ghost-button min-h-9 text-[10px]">Cancel</button>}</div></>}{query.isLoading ? <Loading/> : query.isError ? <p className="error-banner mt-3">Notes could not be loaded.</p> : <div className="mt-4 space-y-2">{query.data?.map((note) => <article key={note.id} className="rounded-lg border border-subtle bg-background/30 p-3"><p className="whitespace-pre-line text-xs leading-5 text-secondary">{note.body}</p><div className="mt-3 flex items-center justify-between gap-2"><span className="text-[9px] text-muted">{note.author_name} · {new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(note.updated_at))}</span>{!readOnly && <span className="flex"><button type="button" onClick={() => { setEditingId(note.id); setBody(note.body) }} className="ghost-button min-h-8 px-2" aria-label="Edit note"><Pencil size={12}/></button><button type="button" onClick={() => remove.mutate(note.id)} className="ghost-button min-h-8 px-2 text-danger" aria-label="Delete note"><Trash2 size={12}/></button></span>}</div></article>)}{!query.data?.length && <PanelEmpty icon={NotebookPen} text="No investigator notes have been added."/>}</div>}</div>
}

function RelationshipNotice({ relationship, caseId, readOnly }: { relationship: PersonRelationship; caseId: string; readOnly: boolean }) {
  const refresh = () => Promise.all([queryClient.invalidateQueries({ queryKey: ['case', caseId, 'relationships'] }), queryClient.invalidateQueries({ queryKey: ['case', caseId, 'people'] })])
  const review = useMutation({ mutationFn: (status: 'confirmed' | 'rejected') => api.reviewRelationship(caseId, relationship.id, status), onSuccess: refresh })
  return <div className="mt-4 rounded-lg border border-purple/30 bg-purple-muted p-3"><p className="text-[9px] font-bold uppercase tracking-[.1em] text-purple">Selected relationship</p><p className="mt-1 text-xs font-semibold text-primary">{relationship.label}</p>{relationship.description && <p className="mt-1 text-[10px] leading-4 text-secondary">{relationship.description}</p>}{!readOnly && relationship.ai_suggested && relationship.review_status === 'suggested' && <div className="mt-2 flex gap-2"><button type="button" onClick={() => review.mutate('confirmed')} className="ghost-button min-h-8 px-2 text-[9px] text-success"><Check size={12}/>Confirm</button><button type="button" onClick={() => review.mutate('rejected')} className="ghost-button min-h-8 px-2 text-[9px] text-danger"><X size={12}/>Reject</button></div>}</div>
}

function PanelEmpty({ icon: Icon, text }: { icon: typeof Network; text: string }) { return <div className="py-8 text-center"><Icon size={22} className="mx-auto text-muted"/><p className="mt-3 text-xs leading-5 text-muted">{text}</p></div> }
function Loading() { return <div className="grid min-h-28 place-items-center"><span className="size-5 animate-spin rounded-full border-2 border-subtle border-t-accent"/></div> }
