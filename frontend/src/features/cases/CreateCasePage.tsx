import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowLeft, CalendarClock, Check, FilePenLine, Search, Sparkles } from 'lucide-react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router'
import { z } from 'zod'
import { UpgradeButton } from '../../components/ui/Visual'
import { APP_NAME } from '../../config/brand'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'

const bannerTemplates = [
  { value: '/case-banners/mountain-trail.jpg', label: 'Mountain trail', description: 'Remote and atmospheric' },
  { value: '/case-banners/coastal-road.jpg', label: 'Coastal road', description: 'Open road and shoreline' },
  { value: '/case-banners/rainy-city.jpg', label: 'Rainy city', description: 'Urban and nocturnal' },
  { value: '/case-banners/desert-road.jpg', label: 'Desert road', description: 'Sparse and isolated' },
  { value: '/case-banners/archive-room.jpg', label: 'Archive room', description: 'Historical and documentary' },
] as const

const bannerValues = bannerTemplates.map((template) => template.value) as [string, ...string[]]

const schema = z.object({
  creation_mode: z.enum(['ai', 'manual']),
  research_clue: z.string().trim().max(500, 'Keep the starting clue under 500 characters').optional(),
  title: z.string().trim().max(500, 'Keep the title under 500 characters').optional(),
  summary: z.string().trim().max(12000, 'Keep the overview under 12,000 characters').optional(),
  banner_template: z.enum(bannerValues).optional(),
}).superRefine((data, context) => {
  if (data.creation_mode === 'ai' && (!data.research_clue || data.research_clue.length < 2)) {
    context.addIssue({ code: 'custom', path: ['research_clue'], message: 'Enter a name, clue, or event' })
  }
  if (data.creation_mode === 'manual') {
    if (!data.title || data.title.length < 2) context.addIssue({ code: 'custom', path: ['title'], message: 'Enter a case title' })
    if (!data.summary || data.summary.length < 20) context.addIssue({ code: 'custom', path: ['summary'], message: 'Write an overview of at least 20 characters' })
    if (!data.banner_template) context.addIssue({ code: 'custom', path: ['banner_template'], message: 'Select a banner template' })
  }
})

type FormData = z.infer<typeof schema>

function formatAllowanceReset(value: string | null | undefined) {
  if (!value) return null
  return new Intl.DateTimeFormat(undefined, {
    weekday: 'long',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZone: 'UTC',
    timeZoneName: 'short',
  }).format(new Date(value))
}

export function CreateCasePage() {
  const navigate = useNavigate()
  const { register, handleSubmit, watch, setValue, clearErrors, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { creation_mode: 'ai' },
  })
  const mode = watch('creation_mode')
  const selectedBanner = watch('banner_template')
  const { data: currentUser } = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const canCreateWithAi = currentUser?.permissions.includes('case.create_ai') ?? false
  const canCreateManually = currentUser?.permissions.includes('case.create') ?? false
  const allowanceReset = formatAllowanceReset(currentUser?.weekly_cases_reset_at)
  const allowanceExhausted = currentUser?.weekly_cases_remaining === 0
  const mutation = useMutation({
    mutationFn: (data: FormData) => data.creation_mode === 'manual'
      ? api.createCase({
          victim_names: data.title!,
          creation_mode: 'manual',
          summary: data.summary,
          banner_template: data.banner_template,
          privacy: 'public',
        })
      : api.createCase({
          victim_names: data.research_clue!,
          creation_mode: 'ai',
          privacy: 'public',
        }),
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: ['cases'] })
      await queryClient.invalidateQueries({ queryKey: ['current-user'] })
      navigate(`/cases/${created.id}`)
    },
  })

  const selectMode = (nextMode: 'ai' | 'manual') => {
    setValue('creation_mode', nextMode)
    clearErrors()
    mutation.reset()
  }

  return <div className="mx-auto max-w-4xl">
    <Link to="/cases" className="ghost-button px-0 text-xs"><ArrowLeft size={15}/> Case directory</Link>

    <header className="mt-8 text-center sm:mt-10">
      <span className="mx-auto grid size-12 place-items-center rounded-xl border border-accent/30 bg-accent-muted text-accent"><Search size={21}/></span>
      <p className="eyebrow mt-6">New investigation</p>
      <h1 className="page-title mt-3">How should this case begin?</h1>
      <p className="mx-auto mt-4 max-w-2xl text-[15px] leading-7 text-secondary">Start with AI-assisted public research, or build the initial case overview yourself.</p>
    </header>

    <div className="mt-8 grid gap-3 sm:grid-cols-2" role="group" aria-label="Case creation method">
      <button type="button" onClick={() => selectMode('ai')} aria-pressed={mode === 'ai'} className={`card flex min-h-28 items-start gap-4 p-5 text-left transition duration-200 ${mode === 'ai' ? 'border-accent bg-accent-muted' : 'hover:border-strong hover:bg-white/[.025]'}`}>
        <span className={`grid size-10 shrink-0 place-items-center rounded-lg border ${mode === 'ai' ? 'border-accent/40 bg-accent-muted text-accent' : 'border-default text-muted'}`}><Sparkles size={18}/></span>
        <span><strong className="block text-sm text-primary">Research with AI</strong><span className="mt-1 block text-xs leading-5 text-secondary">Give {APP_NAME} a person, clue, case name, or event to research.</span></span>
      </button>
      <button type="button" onClick={() => selectMode('manual')} aria-pressed={mode === 'manual'} className={`card flex min-h-28 items-start gap-4 p-5 text-left transition duration-200 ${mode === 'manual' ? 'border-accent bg-accent-muted' : 'hover:border-strong hover:bg-white/[.025]'}`}>
        <span className={`grid size-10 shrink-0 place-items-center rounded-lg border ${mode === 'manual' ? 'border-accent/40 bg-accent-muted text-accent' : 'border-default text-muted'}`}><FilePenLine size={18}/></span>
        <span><strong className="block text-sm text-primary">Create manually</strong><span className="mt-1 block text-xs leading-5 text-secondary">Write the title and overview, then choose a case banner.</span></span>
      </button>
    </div>

    <form className="card mt-5 p-5 sm:p-8" onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <input type="hidden" {...register('creation_mode')}/>

      <div className="mb-6 flex gap-3 rounded-xl border border-accent/25 bg-accent-muted p-4">
        <CalendarClock className="mt-0.5 shrink-0 text-accent" size={18}/>
        {mode === 'manual'
          ? <div><p className="text-sm font-semibold text-primary">Unlimited manual public cases</p><p className="mt-1 text-xs leading-5 text-secondary">This case will be public and will not use your weekly allowance.</p></div>
          : <div><p className="text-sm font-semibold text-primary">{!currentUser ? 'Loading case allowance…' : currentUser.weekly_cases_remaining == null ? 'Unlimited case allowance' : `${currentUser.weekly_cases_remaining} of ${currentUser.weekly_case_limit} cases left this week`}</p>{allowanceReset && <p className="mt-1 text-xs leading-5 text-secondary">Your allowance resets {allowanceReset}.</p>}</div>}
      </div>

      {mode === 'ai' ? <>
        <label className="block text-sm font-semibold text-primary" htmlFor="research-clue">Name, clue, and/or event</label>
        <div className="relative mt-3">
          <Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" size={19}/>
          <input id="research-clue" className="field h-14 pl-12 text-base" placeholder="e.g. Gabby Petito, 2021 disappearance" autoComplete="off" autoFocus {...register('research_clue')}/>
        </div>
        {errors.research_clue && <p className="mt-2 text-xs text-danger-text">{errors.research_clue.message}</p>}
      </> : <div className="space-y-6">
        <div>
          <label className="block text-sm font-semibold text-primary" htmlFor="case-title">Case title</label>
          <input id="case-title" className="field mt-3" placeholder="e.g. The Northpoint disappearance" autoComplete="off" autoFocus {...register('title')}/>
          {errors.title && <p className="mt-2 text-xs text-danger-text">{errors.title.message}</p>}
        </div>

        <div>
          <label className="block text-sm font-semibold text-primary" htmlFor="case-summary">Case overview</label>
          <p className="mt-1 text-xs leading-5 text-muted">Describe what is known and what you want collaborators to investigate.</p>
          <textarea id="case-summary" className="field mt-3 min-h-40 resize-y py-3" placeholder="Write the initial overview of the case…" {...register('summary')}/>
          {errors.summary && <p className="mt-2 text-xs text-danger-text">{errors.summary.message}</p>}
        </div>

        <fieldset>
          <legend className="text-sm font-semibold text-primary">Select a banner</legend>
          <p className="mt-1 text-xs leading-5 text-muted">Choose the image that best fits this case.</p>
          <div className="mt-4 grid grid-cols-1 gap-3 min-[460px]:grid-cols-2 sm:grid-cols-3">
            {bannerTemplates.map((template) => {
              const selected = selectedBanner === template.value
              return <label key={template.value} className={`group relative cursor-pointer overflow-hidden rounded-xl border bg-surface transition duration-200 ${selected ? 'border-accent shadow-[0_0_0_3px_rgba(213,166,74,.09)]' : 'border-subtle hover:border-strong'}`}>
                <input className="sr-only" type="radio" value={template.value} {...register('banner_template')}/>
                <img src={template.value} alt="" className="aspect-[16/9] w-full object-cover transition duration-200 group-hover:scale-[1.02]"/>
                <span className="block p-3">
                  <span className="flex items-center justify-between gap-2 text-xs font-semibold text-primary">{template.label}{selected && <span className="grid size-5 place-items-center rounded-full bg-accent text-background"><Check size={12} strokeWidth={2.5}/></span>}</span>
                  <span className="mt-1 block text-[11px] text-muted">{template.description}</span>
                </span>
              </label>
            })}
          </div>
          {errors.banner_template && <p className="mt-2 text-xs text-danger-text">{errors.banner_template.message}</p>}
        </fieldset>
      </div>}

      {mutation.error && <p role="alert" className="error-banner mt-5">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not create this case'}</p>}

      <div className="mt-7 flex justify-end">
        {mode === 'ai'
          ? canCreateWithAi
            ? <button className="primary-button w-full px-6 sm:w-auto" disabled={mutation.isPending || allowanceExhausted}><Sparkles size={17}/>{mutation.isPending ? 'Starting research…' : allowanceExhausted ? 'Weekly allowance used' : 'Research and create case'}</button>
            : <UpgradeButton requiredTier={2} className="primary-button w-full px-6 sm:w-auto" description="AI-assisted case creation requires an eligible investigation plan.">Research and create case</UpgradeButton>
          : canCreateManually
            ? <button className="primary-button w-full px-6 sm:w-auto" disabled={mutation.isPending}><FilePenLine size={17}/>{mutation.isPending ? 'Creating case…' : 'Create case manually'}</button>
            : <UpgradeButton requiredTier={2} className="primary-button w-full px-6 sm:w-auto" description="Manual case creation is available to Investigator plans and above.">Create case manually</UpgradeButton>}
      </div>
    </form>
  </div>
}
