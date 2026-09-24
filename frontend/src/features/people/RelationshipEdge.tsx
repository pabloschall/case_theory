import { BaseEdge, EdgeLabelRenderer, getBezierPath, type Edge, type EdgeProps } from '@xyflow/react'
import { memo } from 'react'
import type { PersonRelationship } from '../../types'

export type RelationshipGraphEdge = Edge<{ relationship: PersonRelationship; color: string; dimmed: boolean; onInspect: () => void } & Record<string, unknown>, 'relationship'>

export const RelationshipEdge = memo(function RelationshipEdge(props: EdgeProps<RelationshipGraphEdge>) {
  const [path, x, y] = getBezierPath(props)
  const { relationship, color, dimmed } = props.data!
  return <>
    <BaseEdge path={path} style={{ stroke: color, strokeWidth: props.selected ? 2 : 1.25, opacity: dimmed ? .12 : .72 }}/>
    <EdgeLabelRenderer><button type="button" onClick={(event) => { event.stopPropagation(); props.data?.onInspect?.() }} className="nodrag nopan absolute rounded-md border px-2 py-1 text-[9px] font-semibold text-primary shadow-card transition hover:brightness-125" style={{ transform: `translate(-50%, -50%) translate(${x}px,${y}px)`, borderColor: color, background: 'var(--bg-elevated)', opacity: dimmed ? .18 : 1 }}>{relationship.label}{relationship.ai_suggested && relationship.review_status === 'suggested' ? ' · AI' : ''}</button></EdgeLabelRenderer>
  </>
})
