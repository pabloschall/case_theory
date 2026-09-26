import {useState, type FormEvent} from 'react'
import {CheckCircle2, ExternalLink, NotebookPen, Plus, Send, Sparkles} from 'lucide-react'
import {api} from '../../services/api'
import {queryClient} from '../../lib/query'
import type {ResearchAction} from '../../types'

type Message = {
    role: 'user' | 'assistant'
    content: string
    sources?: { title: string; url: string }[]
    action?: ResearchAction | null
}

export function ResearcherChat({caseId, title}: {caseId: string; title: string}) {
    const [messages, setMessages] = useState<Message[]>([])
    const [draft, setDraft] = useState('')
    const [pending, setPending] = useState(false)
    const [error, setError] = useState('')
    const [savingIndex, setSavingIndex] = useState<number | null>(null)
    const [savedIndexes, setSavedIndexes] = useState<Set<number>>(new Set())
    const [runningActionIndex, setRunningActionIndex] = useState<number | null>(null)
    const [completedActionIndexes, setCompletedActionIndexes] = useState<Set<number>>(new Set())

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        const question = draft.trim()
        if (!question || pending) return
        const history = messages.slice(-12).map(({role, content, sources}) => ({role, content, sources: sources ?? []}))
        setMessages((current) => [...current, {role: 'user', content: question}])
        setDraft('')
        setError('')
        setPending(true)
        try {
            const result = await api.researchChat(caseId, {message: question, history})
            setMessages((current) => [...current, {role: 'assistant', content: result.answer, sources: result.sources, action: result.action}])
        } catch (failure) {
            setMessages((current) => current.slice(0, -1))
            setDraft(question)
            setError(failure instanceof Error ? failure.message : 'Research could not be completed.')
        } finally {
            setPending(false)
        }
    }

    async function addToNotes(message: Message, index: number) {
        if (savingIndex !== null || savedIndexes.has(index)) return
        const question = messages[index - 1]?.role === 'user' ? messages[index - 1].content : 'Research answer'
        const sourceList = message.sources?.length
            ? `\n\nSources\n${message.sources.map((source) => `- ${source.title}: ${source.url}`).join('\n')}`
            : ''
        setSavingIndex(index)
        setError('')
        try {
            await api.createNotebookNote(caseId, {
                title: `Research: ${question}`.slice(0, 180),
                body: `${message.content}${sourceList}`,
            })
            setSavedIndexes((current) => new Set(current).add(index))
            await queryClient.invalidateQueries({queryKey: ['case', caseId, 'notebook-notes']})
        } catch (failure) {
            setError(failure instanceof Error ? failure.message : 'The research could not be added to My Notes.')
        } finally {
            setSavingIndex(null)
        }
    }

    async function runAction(action: ResearchAction, index: number) {
        if (runningActionIndex !== null || completedActionIndexes.has(index)) return
        setRunningActionIndex(index)
        setError('')
        try {
            await api.executeResearchAction(caseId, action)
            setCompletedActionIndexes((current) => new Set(current).add(index))
            const queryKey = action.action_type === 'thread'
                ? ['case', caseId, 'discussions']
                : action.action_type === 'evidence'
                    ? ['case', caseId, 'evidence']
                    : ['case', caseId]
            await queryClient.invalidateQueries({queryKey})
        } catch (failure) {
            setError(failure instanceof Error ? failure.message : 'The proposed action could not be completed.')
        } finally {
            setRunningActionIndex(null)
        }
    }

    return <section className="card mx-auto flex min-h-[60vh] max-w-4xl flex-col overflow-hidden">
        <div className="border-b border-subtle p-5 sm:p-6">
            <h2 className="section-title flex items-center gap-2"><Sparkles size={19} className="text-accent"/> Researcher</h2>
            <p className="mt-2 text-sm leading-6 text-secondary">Ask about {title}. The researcher uses this case’s title and overview, searches public web sources, and links the sources it finds.</p>
        </div>
        <div className="flex-1 space-y-5 p-5 sm:p-6" aria-live="polite">
            {messages.map((message, index) => <div key={index} className={message.role === 'user' ? 'ml-auto max-w-[85%] rounded-xl bg-accent-muted p-4 text-sm text-primary' : 'max-w-[95%] rounded-xl border border-subtle bg-tertiary/50 p-4 text-sm text-secondary'}>
                <p className="whitespace-pre-wrap leading-6">{message.content}</p>
                {message.sources && message.sources.length > 0 && <div className="mt-4 border-t border-subtle pt-3">
                    <p className="eyebrow">Web sources</p>
                    <ul className="mt-2 space-y-2">{message.sources.map((source) => <li key={source.url}><a className="inline-flex max-w-full items-center gap-1 text-xs text-blue hover:text-primary" href={source.url} target="_blank" rel="noopener noreferrer"><span className="truncate">{source.title}</span><ExternalLink size={12} className="shrink-0"/></a></li>)}</ul>
                </div>}{message.action && <div className="mt-4 rounded-lg border border-accent/30 bg-accent-muted/35 p-4">
                    <p className="eyebrow">Proposed action</p>
                    <p className="mt-2 text-sm font-semibold text-primary">{message.action.payload.title}</p>
                    <p className="mt-1 text-xs leading-5 text-secondary">{actionDescription(message.action)}</p>
                    <p className="mt-2 font-mono text-[10px] text-muted">POST {message.action.endpoint}</p>
                    <button type="button" onClick={() => runAction(message.action!, index)} disabled={runningActionIndex !== null || completedActionIndexes.has(index)} className="primary-button mt-3 min-h-9 w-fit px-3 text-[11px]">{completedActionIndexes.has(index) ? <CheckCircle2 size={14}/> : <Plus size={14}/>} {completedActionIndexes.has(index) ? 'Created' : runningActionIndex === index ? 'Creating…' : message.action.label}</button>
                </div>}{message.role === 'assistant' && <button type="button" onClick={() => addToNotes(message, index)} disabled={savingIndex !== null || savedIndexes.has(index)} className="secondary-button mt-4 min-h-9 w-fit px-3 text-[11px]"><NotebookPen size={14}/>{savedIndexes.has(index) ? 'Saved to My Notes' : savingIndex === index ? 'Saving…' : 'Add to My Notes'}</button>}
            </div>)}
            {pending && <p className="flex items-center gap-2 text-sm text-muted"><Sparkles size={14} className="animate-pulse"/> Searching public sources…</p>}
        </div>
        <form onSubmit={submit} className="border-t border-subtle p-5 sm:p-6">
            {error && <p role="alert" className="error-banner mb-3">{error}</p>}
            <label htmlFor="research-question" className="sr-only">Ask the researcher</label>
            <div className="flex items-end gap-3"><textarea id="research-question" className="field min-h-20 flex-1 resize-y py-3" maxLength={2000} value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Ask a question about this case…" onKeyDown={(event) => {if (event.key === 'Enter' && !event.shiftKey) {event.preventDefault(); event.currentTarget.form?.requestSubmit()}}}/><button className="primary-button shrink-0" type="submit" disabled={pending || !draft.trim()}><Send size={15}/> Send</button></div>
            <p className="mt-2 text-xs text-muted">Answers may be incomplete. Check the linked sources before relying on a claim.</p>
        </form>
    </section>
}

function actionDescription(action: ResearchAction) {
    if (action.action_type === 'timeline') return `${action.payload.occurred_on} · ${action.payload.description}`
    if (action.action_type === 'thread') return `${action.payload.thread_type.replaceAll('_', ' ')} · ${action.payload.body}`
    return `${action.payload.evidence_type} · ${action.payload.url}`
}
