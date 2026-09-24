import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowUpCircle, Camera, LogOut, ShieldCheck, Undo2, UserRoundX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { z } from 'zod'
import { PageHeader, UpgradeButton } from '../../components/ui/Visual'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'

const schema = z.object({
  display_name: z.string().trim().min(1, 'Enter your display name').max(80),
  username: z.string().trim().min(3).max(40).regex(/^[a-zA-Z0-9_]+$/, 'Use letters, numbers, and underscores'),
  bio: z.string().max(1000, 'Keep your bio under 1,000 characters'),
})
type ProfileForm = z.infer<typeof schema>

const tierNames: Record<number, string> = {
  0: 'Administrator',
  1: 'Free',
  2: 'Investigator',
  3: 'Lead Investigator',
}

export function ProfilePage() {
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const [avatarError, setAvatarError] = useState('')
  const { data: user } = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const blocked = useQuery({ queryKey: ['blocked-users'], queryFn: api.blockedUsers })
  const { register, handleSubmit, reset, formState: { errors, isDirty } } = useForm<ProfileForm>({ resolver: zodResolver(schema), defaultValues: { display_name: '', username: '', bio: '' } })
  useEffect(() => { if (user) reset({ display_name: user.display_name, username: user.username, bio: user.bio ?? '' }) }, [user, reset])
  const save = useMutation({ mutationFn: api.updateProfile, onSuccess: (updated) => { queryClient.setQueryData(['current-user'], updated); reset({ display_name: updated.display_name, username: updated.username, bio: updated.bio ?? '' }) } })
  const avatar = useMutation({ mutationFn: async (file: File) => { const contentType = file.type || imageType(file.name); const ticket = await api.requestAvatarUpload({ filename: file.name, content_type: contentType, file_size: file.size }); const response = await fetch(ticket.upload_url, { method: ticket.upload_method, headers: ticket.upload_headers, body: file }); if (!response.ok) throw new Error('Storage rejected the image'); return api.completeAvatarUpload(ticket.upload_id) }, onSuccess: (updated) => { queryClient.setQueryData(['current-user'], updated); setAvatarError('') }, onError: (error) => setAvatarError(error instanceof Error ? error.message : 'Profile picture upload failed') })
  const unblock = useMutation({ mutationFn: api.unblockUser, onSuccess: () => { void queryClient.invalidateQueries({ queryKey: ['blocked-users'] }); void queryClient.invalidateQueries({ queryKey: ['member'] }) } })
  const logout = useMutation({ mutationFn: api.logout, onSuccess: () => { queryClient.clear(); navigate('/login') } })
  const verification = useMutation({ mutationFn: () => api.requestEmailVerification(user?.email ?? '') })
  const initials = user?.display_name.split(/\s+/).slice(0, 2).map((part) => part[0]).join('').toUpperCase() ?? ''
  const tierName = user ? tierNames[user.tier_level] ?? user.plan_code : ''
  return <div className="mx-auto max-w-2xl">
    <PageHeader eyebrow="Account record" title="Your workspace identity." description="Keep your public investigator profile current and manage who can contact you."/>
    <section className="card mt-8 overflow-hidden">
      <div className="flex flex-col gap-5 border-b border-subtle p-6 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-4"><div className="grid size-20 shrink-0 place-items-center overflow-hidden rounded-full border border-info/40 bg-blue-muted font-display text-xl font-semibold text-blue">{user?.avatar_url ? <img src={user.avatar_url} alt="Your profile" className="size-full object-cover"/> : initials}</div>
          <div className="min-w-0 flex-1"><h2 className="section-title truncate">{user?.display_name}</h2><p className="metadata mt-1">@{user?.username}</p><button type="button" onClick={() => fileInput.current?.click()} disabled={avatar.isPending} className="secondary-button mt-3 min-h-10 px-3 text-xs"><Camera size={15}/>{avatar.isPending ? 'Uploading…' : 'Change picture'}</button><input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif" className="sr-only" onChange={(event) => { const file = event.target.files?.[0]; if (file) avatar.mutate(file); event.target.value = '' }}/></div></div>
        <div className="flex shrink-0 flex-col gap-2 border-t border-subtle pt-4 sm:w-52 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0"><div className="rounded-lg border border-accent/25 bg-accent-muted px-3 py-2"><p className="eyebrow text-accent">Current tier</p><p className="mt-1 text-sm font-semibold text-primary">{tierName}</p>{user && <p className="mt-1 text-[11px] text-secondary">{user.weekly_cases_remaining ?? 'Unlimited'} of {user.weekly_case_limit < 0 ? 'unlimited' : user.weekly_case_limit} limited cases left this week</p>}</div>{user && user.tier_level === 1 && <UpgradeButton className="secondary-button w-full text-xs" description="Upgrade to create up to five limited cases each week. Manual public cases are unlimited."><ArrowUpCircle size={15}/> Upgrade plan</UpgradeButton>}<button onClick={() => logout.mutate()} disabled={logout.isPending} className="ghost-button w-full justify-start border border-subtle text-xs text-secondary"><LogOut size={16}/>{logout.isPending ? 'Signing out…' : 'Sign out'}</button></div>
      </div>
      {avatarError && <p className="mx-6 mt-5 text-xs text-danger">{avatarError}</p>}
      <form onSubmit={handleSubmit((data) => save.mutate(data))} className="space-y-5 p-6">
        <Field label="Display name" error={errors.display_name?.message}><input className="field mt-2" autoComplete="name" {...register('display_name')}/></Field>
        <Field label="Username" error={errors.username?.message}><div className="relative mt-2"><span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted">@</span><input className="field pl-8" autoComplete="username" {...register('username')}/></div></Field>
        <Field label="Bio" error={errors.bio?.message}><textarea className="field mt-2 min-h-28 resize-y py-3" placeholder="Share your research interests or experience." {...register('bio')}/></Field>
        {save.error && <p className="text-xs text-danger">{save.error instanceof ApiError ? save.error.message : 'Profile could not be saved.'}</p>}
        {save.isSuccess && !isDirty && <p className="text-xs text-success">Profile updated.</p>}
        <button type="submit" disabled={save.isPending || !isDirty} className="primary-button w-full">{save.isPending ? 'Saving…' : 'Save profile'}</button>
      </form>
      <dl className="divide-y divide-subtle border-t border-subtle px-6 text-sm"><div className="flex justify-between gap-4 py-4"><dt className="text-muted">Email</dt><dd className="truncate font-semibold text-primary">{user?.email}</dd></div><div className="flex items-center justify-between gap-4 py-4"><dt className="text-muted">Email status</dt><dd className="flex items-center gap-3"><span className="inline-flex items-center gap-1 font-semibold text-primary"><ShieldCheck size={16}/>{user?.is_verified ? 'Verified' : 'Verification pending'}</span>{user && !user.is_verified && <button type="button" className="secondary-button min-h-8 px-3 text-xs" disabled={verification.isPending} onClick={() => verification.mutate()}>{verification.isPending ? 'Sending…' : verification.isSuccess ? 'Sent' : 'Resend'}</button>}</dd></div></dl>
    </section>
    <section className="card mt-6 p-6"><div className="flex items-center gap-2"><UserRoundX size={17} className="text-muted"/><h2 className="section-title">Blocked members</h2></div>{blocked.isLoading && <p className="mt-4 text-xs text-muted">Loading blocked members…</p>}{blocked.data?.length === 0 && <p className="mt-4 text-sm text-muted">You have not blocked anyone.</p>}<div className="mt-4 divide-y divide-subtle">{blocked.data?.map((member) => <div key={member.id} className="flex items-center justify-between gap-3 py-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-primary">{member.display_name}</p><p className="metadata mt-1">@{member.username}</p></div><button type="button" onClick={() => unblock.mutate(member.id)} disabled={unblock.isPending} className="secondary-button min-h-10 px-3 text-xs"><Undo2 size={14}/>Unblock</button></div>)}</div></section>
  </div>
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) { return <label className="block text-xs font-semibold text-secondary">{label}{children}{error && <span className="mt-1 block font-normal text-danger">{error}</span>}</label> }

function imageType(filename: string) { const extension = filename.split('.').pop()?.toLowerCase(); if (extension === 'png') return 'image/png'; if (extension === 'webp') return 'image/webp'; if (extension === 'heic') return 'image/heic'; if (extension === 'heif') return 'image/heif'; return 'image/jpeg' }
