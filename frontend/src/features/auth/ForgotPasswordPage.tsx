import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { z } from 'zod'
import { AuthLayout } from '../../components/AuthLayout'
import { ApiError, api } from '../../services/api'

const schema = z.object({ email: z.email('Enter a valid email') })
type FormData = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) })
  const mutation = useMutation({ mutationFn: ({ email }: FormData) => api.forgotPassword(email) })

  return <AuthLayout eyebrow="Account recovery" title="Reset your password." description="Enter your account email and we will send a one-time reset link." footer={<Link className="font-semibold text-accent" to="/login">Return to sign in</Link>}>
    {mutation.isSuccess ? <div className="space-y-4"><p className="success-banner">If an account exists for that email, a reset link is on its way.</p><p className="text-sm text-secondary">Check your inbox and spam folder. The link expires in 60 minutes.</p></div> : <form className="space-y-5" onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <label className="block text-sm font-semibold">Email<input className="field mt-2" type="email" autoComplete="email" {...register('email')} /></label>
      {errors.email && <p className="-mt-3 text-sm text-danger-text">{errors.email.message}</p>}
      {mutation.error && <p role="alert" className="error-banner">{mutation.error instanceof ApiError ? mutation.error.message : 'Could not request a reset link'}</p>}
      <button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? 'Sending…' : 'Send reset link'}</button>
    </form>}
  </AuthLayout>
}
