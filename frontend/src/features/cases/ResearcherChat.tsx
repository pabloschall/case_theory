import {useState, type FormEvent} from 'react'
import {ExternalLink, Send, Sparkles} from 'lucide-react'
import {api} from '../../services/api'

type Message = {
    role: 'user' | 'assistant'
    content: string
    sources?: { title: string; url: string }[]
}

export function ResearcherChat({caseId, title}: {caseId: string; title: string}) {
    const [messages, setMessages] = useState<Message[]>([])
    const [draft, setDraft] = useState('')
    const [pending, setPending] = useState(false)
    const [error, setError] = useState('')

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault()
        const question = draft.trim()
        if (!question || pending) return
        const history = messages.slice(-12).map(({role, content}) => ({role, content}))
        setMessages((current) => [...current, {role: 'user', content: question}])
        setDraft('')
        setError('')
        setPending(true)
        try {
            const result = await api.researchChat(caseId, {message: question, history})
            setMessages((current) => [...current, {role: 'assistant', content: result.answer, sources: result.sources}])
        } catch (failure) {
            setMessages((current) => current.slice(0, -1))
            setDraft(question)
            setError(failure instanceof Error ? failure.message : 'Research could not be completed.')
        } finally {
            setPending(false)
        }
    }

    return <section className="card mx-auto flex min-h-[60vh] max-w-4xl flex-col overflow-hidden">
        <div className="border-b border-subtle p-5 sm:p-6">
            <h2 className="section-title flex items-center gap-2"><Sparkles size={19} className="text-accent"/> Chat Researcher</h2>
            <p className="mt-2 text-sm leading-6 text-secondary">Ask about {title}. The researcher uses this case’s title and overview, searches public web sources, and links the sources it finds.</p>
        </div>
        <div className="flex-1 space-y-5 p-5 sm:p-6" aria-live="polite">
            {messages.length === 0 && <p className="text-sm text-muted">What would you like to research about this case?</p>}
            {messages.map((message, index) => <div key={index} className={message.role === 'user' ? 'ml-auto max-w-[85%] rounded-xl bg-accent-muted p-4 text-sm text-primary' : 'max-w-[95%] rounded-xl border border-subtle bg-tertiary/50 p-4 text-sm text-secondary'}>
                <p className="whitespace-pre-wrap leading-6">{message.content}</p>
                {message.sources && message.sources.length > 0 && <div className="mt-4 border-t border-subtle pt-3">
                    <p className="eyebrow">Web sources</p>
                    <ul className="mt-2 space-y-2">{message.sources.map((source) => <li key={source.url}><a className="inline-flex max-w-full items-center gap-1 text-xs text-blue hover:text-primary" href={source.url} target="_blank" rel="noopener noreferrer"><span className="truncate">{source.title}</span><ExternalLink size={12} className="shrink-0"/></a></li>)}</ul>
                </div>}
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
