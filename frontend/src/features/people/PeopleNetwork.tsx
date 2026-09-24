import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Background,
  Controls,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type NodeMouseHandler,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { CasePerson, PersonRelationship } from '../../types'
import { PersonNode, type PersonGraphNode } from './PersonNode'
import { RelationshipEdge, type RelationshipGraphEdge } from './RelationshipEdge'
import { relationshipColor } from './config'

const nodeTypes = { person: PersonNode }
const edgeTypes = { relationship: RelationshipEdge }

export function PeopleNetwork({ people, relationships, selectedId, onSelect, onInspectRelationship }: { people: CasePerson[]; relationships: PersonRelationship[]; selectedId: string | null; onSelect: (id: string) => void; onInspectRelationship: (relationship: PersonRelationship) => void }) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [nodes, setNodes, onNodesChange] = useNodesState<PersonGraphNode>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<RelationshipGraphEdge>([])
  const focusId = hoveredId ?? selectedId
  const positions = useMemo(() => layoutPeople(people), [people])
  const peopleById = useMemo(() => new Set(people.map((person) => person.id)), [people])
  const relatedIds = useMemo(() => {
    if (!focusId) return new Set<string>()
    const ids = new Set([focusId])
    relationships.forEach((relationship) => {
      if (relationship.source_person_id === focusId) ids.add(relationship.target_person_id)
      if (relationship.target_person_id === focusId) ids.add(relationship.source_person_id)
    })
    return ids
  }, [focusId, relationships])

  useEffect(() => {
    setNodes((current) => {
      const existing = new Map(current.map((node) => [node.id, node]))
      return people.map((person) => ({
        id: person.id,
        type: 'person',
        position: existing.get(person.id)?.position ?? positions.get(person.id) ?? { x: 0, y: 0 },
        data: {
          person,
          active: person.id === focusId,
          dimmed: Boolean(focusId && !relatedIds.has(person.id)),
        },
        selected: person.id === selectedId,
        style: { width: 144 },
      }))
    })
  }, [people, positions, focusId, relatedIds, selectedId, setNodes])

  useEffect(() => {
    setEdges(relationships.filter((relationship) => peopleById.has(relationship.source_person_id) && peopleById.has(relationship.target_person_id)).map((relationship) => {
      const connected = !focusId || relationship.source_person_id === focusId || relationship.target_person_id === focusId
      return {
        id: relationship.id,
        source: relationship.source_person_id,
        target: relationship.target_person_id,
        type: 'relationship',
        data: {
          relationship,
          color: relationshipColor(relationship.relationship_type),
          dimmed: !connected,
          onInspect: () => onInspectRelationship(relationship),
        },
        zIndex: connected ? 2 : 0,
      }
    }))
  }, [relationships, peopleById, focusId, onInspectRelationship, setEdges])

  const enter = useCallback<NodeMouseHandler<PersonGraphNode>>((_, node) => setHoveredId(node.id), [])
  const leave = useCallback(() => setHoveredId(null), [])
  const click = useCallback<NodeMouseHandler<PersonGraphNode>>((_, node) => onSelect(node.id), [onSelect])

  return <div className="h-[520px] overflow-hidden rounded-xl border border-subtle bg-[#0A1015] shadow-card lg:h-[640px]">
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onNodeClick={click}
      onNodeMouseEnter={enter}
      onNodeMouseLeave={leave}
      fitView
      fitViewOptions={{ padding: .2 }}
      minZoom={.35}
      maxZoom={1.7}
      nodeDragThreshold={8}
      paneClickDistance={8}
      nodesDraggable
      nodesConnectable={false}
      panOnDrag
      zoomOnPinch
      zoomOnScroll
      selectionOnDrag={false}
      onlyRenderVisibleElements
    >
      <Background color="rgba(170,181,190,.06)" gap={28} size={1}/>
      <Controls showInteractive={false} className="!border-default !bg-elevated !shadow-card [&>button]:!border-subtle [&>button]:!bg-elevated [&>button]:!fill-current [&>button]:!text-secondary"/>
    </ReactFlow>
  </div>
}

function layoutPeople(people: CasePerson[]) {
  const result = new Map<string, { x: number; y: number }>()
  if (!people.length) return result
  const primary = people.find((person) => person.is_primary) ?? people[0]
  result.set(primary.id, { x: 310, y: 230 })
  const others = people.filter((person) => person.id !== primary.id)
  const radiusX = Math.max(245, Math.min(390, 210 + others.length * 15))
  const radiusY = Math.max(185, Math.min(290, 165 + others.length * 10))
  others.forEach((person, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(others.length, 1)
    const ring = index >= 8 ? 1.45 : 1
    result.set(person.id, { x: 310 + Math.cos(angle) * radiusX * ring, y: 230 + Math.sin(angle) * radiusY * ring })
  })
  return result
}
