import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { Volume2, VolumeX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { z } from 'zod'
import { AuthLayout } from '../../components/AuthLayout'
import { APP_NAME } from '../../config/brand'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'

const schema = z.object({ email: z.email('Enter a valid email'), password: z.string().min(1, 'Enter your password') })
type FormData = z.infer<typeof schema>

export function LoginPage() {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [soundPlaying, setSoundPlaying] = useState(false)
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const requestedNext = searchParams.get('next')
  const next = requestedNext?.startsWith('/invite/') ? requestedNext : '/cases'
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) })
  const mutation = useMutation({
    mutationFn: api.login,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['current-user'] })
      const user = await queryClient.fetchQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
      const destination = next === '/cases' && user.permissions.includes('admin.access') ? '/admin/users' : next
      navigate(destination)
    },
  })

  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    audio.volume = 0.32
    void audio.play().catch(() => setSoundPlaying(false))
    return () => { audio.pause(); audio.currentTime = 0 }
  }, [])

  const toggleSound = () => {
    const audio = audioRef.current
    if (!audio) return
    if (audio.paused) void audio.play().catch(() => setSoundPlaying(false))
    else audio.pause()
  }

  return <AuthLayout metal signinBackground eyebrow="Welcome back" title="Continue the work." description="Sign in to your investigation workspace. Your session stays protected in secure browser cookies." footer={<>New to {APP_NAME}? <Link className="font-semibold text-accent" to={`/register${next !== '/cases' ? `?next=${encodeURIComponent(next)}` : ''}`}>Create an account</Link></>}>
    <audio ref={audioRef} src="/landing_2.mp3" preload="auto" onPlay={() => setSoundPlaying(true)} onPause={() => setSoundPlaying(false)} onEnded={() => setSoundPlaying(false)}/>
    <form className="space-y-5" onSubmit={handleSubmit((data) => mutation.mutate(data))}>
      <label className="block text-sm font-semibold">Email<input className="field mt-2" type="email" autoComplete="email" {...register('email')} /></label>
      {errors.email && <p className="-mt-3 text-sm text-danger-text">{errors.email.message}</p>}
      <label className="block text-sm font-semibold">Password<input className="field mt-2" type="password" autoComplete="current-password" {...register('password')} /></label>
      {errors.password && <p className="-mt-3 text-sm text-danger-text">{errors.password.message}</p>}
      <div className="-mt-2 text-right"><Link className="text-xs font-semibold text-accent" to="/forgot-password">Forgot password?</Link></div>
      {mutation.error && <p role="alert" className="error-banner">{mutation.error instanceof ApiError ? mutation.error.message : 'Sign in failed'}</p>}
      <button className="primary-button" disabled={mutation.isPending}>{mutation.isPending ? 'Signing in…' : 'Sign in'}</button>
      <button type="button" onClick={toggleSound} className="ghost-button min-h-9 w-full text-[11px]" aria-label={soundPlaying ? 'Pause soundtrack' : 'Play soundtrack'}>{soundPlaying ? <Volume2 size={14}/> : <VolumeX size={14}/>} {soundPlaying ? 'Pause soundtrack' : 'Play soundtrack'}</button>
    </form>
  </AuthLayout>
}
