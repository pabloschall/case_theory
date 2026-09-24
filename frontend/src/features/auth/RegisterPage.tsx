import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'
import type { ReactNode } from 'react'
import { AuthLayout } from '../../components/AuthLayout'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'

const schema = z.object({ display_name: z.string().min(1, 'Enter your name').max(80), username: z.string().min(3).max(40).regex(/^[a-zA-Z0-9_]+$/, 'Use letters, numbers, and underscores'), email: z.email('Enter a valid email'), password: z.string().min(12, 'Use at least 12 characters').regex(/[A-Za-z]/, 'Add a letter').regex(/[0-9]/, 'Add a number'), confirm_age_18: z.literal(true, { error: 'You must be at least 18 to create an account' }), accept_terms: z.literal(true, { error: 'Accept the Terms of Use to continue' }), accept_community_standards: z.literal(true, { error: 'Accept the Community Standards to continue' }) })
type FormData = z.infer<typeof schema>

export function RegisterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedNext = searchParams.get('next')
  const next = requestedNext?.startsWith('/invite/') ? requestedNext : '/cases'
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) })
  const mutation = useMutation({ mutationFn: api.register, onSuccess: async (_, data) => { await queryClient.invalidateQueries({ queryKey: ['current-user'] }); navigate(`/verify-email?email=${encodeURIComponent(data.email)}&next=${encodeURIComponent(next)}`) } })
  return <AuthLayout eyebrow="Create an account" title="Build a sourced record." description="Every workspace includes case research, evidence, timelines, maps, discussions, and people connections." footer={<>Already have an account? <Link className="font-semibold text-accent" to={`/login${next !== '/cases' ? `?next=${encodeURIComponent(next)}` : ''}`}>Sign in</Link></>}>
    <form className="space-y-4" onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <Field label="Display name" error={errors.display_name?.message}><input className="field mt-2" autoComplete="name" {...register('display_name')} /></Field>
      <Field label="Username" error={errors.username?.message}><input className="field mt-2" autoComplete="username" {...register('username')} /></Field>
      <Field label="Email" error={errors.email?.message}><input className="field mt-2" type="email" autoComplete="email" {...register('email')} /></Field>
      <Field label="Password" error={errors.password?.message}><input className="field mt-2" type="password" autoComplete="new-password" {...register('password')} /></Field>
      <div className="space-y-3 rounded-lg border border-subtle bg-background/45 p-4">
        <ConsentField error={errors.confirm_age_18?.message}><input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-[var(--accent-primary)]" {...register('confirm_age_18')}/><span>I confirm that I am at least 18 years old.</span></ConsentField>
        <ConsentField error={errors.accept_terms?.message}><input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-[var(--accent-primary)]" {...register('accept_terms')}/><span>I agree to the <Link to="/terms" target="_blank" className="font-semibold text-accent underline-offset-2 hover:underline">Terms of Use</Link>.</span></ConsentField>
        <ConsentField error={errors.accept_community_standards?.message}><input type="checkbox" className="mt-0.5 size-4 shrink-0 accent-[var(--accent-primary)]" {...register('accept_community_standards')}/><span>I agree to the <Link to="/community-standards" target="_blank" className="font-semibold text-accent underline-offset-2 hover:underline">Community Standards</Link>, including no harassment, doxxing, reckless accusations, or illegal uploads.</span></ConsentField>
      </div>
      {mutation.error && <p role="alert" className="error-banner">{mutation.error instanceof ApiError ? mutation.error.message : 'Registration failed'}</p>}
      <button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? 'Creating account…' : 'Create free account'}</button>
    </form>
  </AuthLayout>
}

function Field({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return <label className="block text-sm font-semibold text-primary">{label}{children}{error && <span className="mt-1 block font-normal text-danger-text">{error}</span>}</label>
}

function ConsentField({ error, children }: { error?: string; children: ReactNode }) {
  return <label className="block text-xs leading-5 text-secondary"><span className="flex items-start gap-3">{children}</span>{error && <span className="ml-7 mt-1 block text-danger-text">{error}</span>}</label>
}
