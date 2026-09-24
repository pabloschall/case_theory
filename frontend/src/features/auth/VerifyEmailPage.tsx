import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router'
import { z } from 'zod'
import { AuthLayout } from '../../components/AuthLayout'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'

const schema = z.object({ email: z.email('Enter a valid email') })
type FormData = z.infer<typeof schema>

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const email = params.get('email') ?? ''
  const requestedNext = params.get('next')
  const next = requestedNext?.startsWith('/') ? requestedNext : '/cases'
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema), defaultValues: { email } })
  const confirmation = useMutation({ mutationFn: api.confirmEmail, onSuccess: () => queryClient.invalidateQueries({ queryKey: ['current-user'] }) })
  const { mutate: confirmEmail } = confirmation
  const resend = useMutation({ mutationFn: ({ email: address }: FormData) => api.requestEmailVerification(address) })

  useEffect(() => { if (token) confirmEmail(token) }, [confirmEmail, token])

  return <AuthLayout eyebrow="Email verification" title={token ? 'Confirming your email.' : 'Check your inbox.'} description="Verification protects your account and unlocks the free AI case trial." footer={<Link className="font-semibold text-accent" to="/login">Return to sign in</Link>}>
    {token ? <div className="space-y-4">
      {confirmation.isPending && <p className="text-sm text-secondary">Verifying your link…</p>}
      {confirmation.isSuccess && <><p className="success-banner">Your email is verified.</p><Link className="primary-button" to={next}>Continue</Link></>}
      {confirmation.error && <p role="alert" className="error-banner">{confirmation.error instanceof ApiError ? confirmation.error.message : 'Could not verify this link'}</p>}
    </div> : <form className="space-y-5" onSubmit={handleSubmit((data) => resend.mutate(data))}>
      <p className="text-sm text-secondary">We sent a verification link when your account was created. You can request another one below.</p>
      <label className="block text-sm font-semibold">Email<input className="field mt-2" type="email" autoComplete="email" {...register('email')} /></label>
      {errors.email && <p className="-mt-3 text-sm text-danger-text">{errors.email.message}</p>}
      {resend.isSuccess && <p className="success-banner">If the account needs verification, a new link has been sent.</p>}
      {resend.error && <p role="alert" className="error-banner">{resend.error instanceof ApiError ? resend.error.message : 'Could not send a verification email'}</p>}
      <button className="primary-button" disabled={resend.isPending}>{resend.isPending ? 'Sending…' : 'Resend verification email'}</button>
    </form>}
  </AuthLayout>
}
