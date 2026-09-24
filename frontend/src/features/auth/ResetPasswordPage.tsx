import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link, useSearchParams } from 'react-router'
import { z } from 'zod'
import { AuthLayout } from '../../components/AuthLayout'
import { ApiError, api } from '../../services/api'

const schema = z.object({
  password: z.string().min(12, 'Use at least 12 characters').regex(/[A-Za-z]/, 'Add a letter').regex(/[0-9]/, 'Add a number'),
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, { path: ['confirmPassword'], message: 'Passwords do not match' })
type FormData = z.infer<typeof schema>

export function ResetPasswordPage() {
  const [params] = useSearchParams()
  const token = params.get('token') ?? ''
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) })
  const mutation = useMutation({ mutationFn: (data: FormData) => api.resetPassword({ token, password: data.password }) })

  return <AuthLayout eyebrow="Account recovery" title="Choose a new password." description="Your new password must be at least 12 characters and include a letter and a number." footer={<Link className="font-semibold text-accent" to="/login">Return to sign in</Link>}>
    {!token ? <p role="alert" className="error-banner">This reset link is incomplete. Request a new one.</p> : mutation.isSuccess ? <div className="space-y-4"><p className="success-banner">Your password has been reset.</p><Link className="primary-button" to="/login">Sign in</Link></div> : <form className="space-y-5" onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <label className="block text-sm font-semibold">New password<input className="field mt-2" type="password" autoComplete="new-password" {...register('password')} /></label>
      {errors.password && <p className="-mt-3 text-sm text-danger-text">{errors.password.message}</p>}
      <label className="block text-sm font-semibold">Confirm password<input className="field mt-2" type="password" autoComplete="new-password" {...register('confirmPassword')} /></label>
      {errors.confirmPassword && <p className="-mt-3 text-sm text-danger-text">{errors.confirmPassword.message}</p>}
      {mutation.error && <p role="alert" className="error-banner">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not reset your password'}</p>}
      <button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? 'Resetting…' : 'Reset password'}</button>
    </form>}
  </AuthLayout>
}
