import { Building2, MapPin, UserRound } from 'lucide-react'
import { Handle, Position, type Node, type NodeProps } from '@xyflow/react'
import { memo } from 'react'
import type { CasePerson } from '../../types'
import { categoryConfig } from './config'

export type PersonGraphNode = Node<{ person: CasePerson; active: boolean; dimmed: boolean } & Record<string, unknown>, 'person'>

export const PersonNode = memo(function PersonNode({ data }: NodeProps<PersonGraphNode>) {
  const { person, active, dimmed } = data
  const category = categoryConfig[person.category]
  const initials = person.name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase()
  const Icon = person.entity_type === 'organization' ? Building2 : person.entity_type === 'location' ? MapPin : UserRound
  const size = person.is_primary ? 'size-[86px]' : 'size-[66px]'
  return <div className={`relative w-36 text-center transition duration-200 ${dimmed ? 'opacity-25 grayscale' : 'opacity-100'} ${active ? 'scale-105' : ''}`}>
    <Handle type="target" position={Position.Top} className="!pointer-events-none !border-0 !bg-transparent"/>
    <div className={`mx-auto grid ${size} place-items-center overflow-hidden rounded-full border-2 bg-elevated shadow-card transition duration-200 ${category.ring} ${active ? 'shadow-[0_0_0_5px_rgba(213,166,74,.10),0_8px_28px_rgba(0,0,0,.35)]' : ''}`}>
      {person.photo_url ? <img src={person.photo_url} alt="" className="size-full object-cover"/> : person.entity_type === 'person' ? <span className="font-display text-xl font-semibold text-primary">{initials}</span> : <Icon size={person.is_primary ? 30 : 24} className="text-secondary"/>}
    </div>
    <p className="mt-2 truncate text-xs font-semibold text-primary">{person.name}</p>
    <p className="mt-0.5 truncate text-[10px] font-medium" style={{ color: category.color }}>{person.role}</p>
    {person.ai_suggested && person.review_status === 'suggested' && <span className="mt-1 inline-flex rounded border border-accent/30 bg-accent-muted px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-[.08em] text-accent">AI suggested</span>}
    <Handle type="source" position={Position.Bottom} className="!pointer-events-none !border-0 !bg-transparent"/>
  </div>
})
