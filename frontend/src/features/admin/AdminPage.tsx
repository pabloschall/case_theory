import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight, ExternalLink, Flag, Search, Shield, Sparkles, Trash2, UserCog, UserPlus, Users, X } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'
import { z } from 'zod'
import { PageHeader, StatusBadge } from '../../components/ui/Visual'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'
import type { AdminCaseListItem, AdminUserListItem } from '../../types'

const tierOptions = [
  { value: 0, label: 'Tier 0 · Admin' },
  { value: 1, label: 'Tier 1 · Free' },
  { value: 2, label: 'Tier 2 · Investigator' },
  { value: 3, label: 'Tier 3 · Lead' },
] as const

const createAdminSchema = z.object({
  email: z.email('Enter a valid email address'),
  username: z.string().min(3, 'Use at least 3 characters').max(40).regex(/^[a-zA-Z0-9_]+$/, 'Use letters, numbers, and underscores only'),
  display_name: z.string().trim().min(1, 'Enter a display name').max(80),
  password: z.string().min(8, 'Use at least 8 characters').max(128).refine((value) => /[A-Za-z]/.test(value) && /\d/.test(value), 'Include at least one letter and one number'),
  confirm_password: z.string(),
}).refine((data) => data.password === data.confirm_password, { message: 'Passwords do not match', path: ['confirm_password'] })

type CreateAdminForm = z.infer<typeof createAdminSchema>

function useDebouncedValue(value: string, delay = 400) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timeout = window.setTimeout(() => setDebounced(value.trim()), delay)
    return () => window.clearTimeout(timeout)
  }, [delay, value])
  return debounced
}

export function AdminUsersPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const query = useDebouncedValue(search)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<CreateAdminForm>({ resolver: zodResolver(createAdminSchema) })
  const currentUser = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const users = useQuery({ queryKey: ['admin', 'users', query, page], queryFn: () => api.adminUsers(query, page) })
  const createAdmin = useMutation({
    mutationFn: (data: CreateAdminForm) => api.createAdminUser({ email: data.email, username: data.username, display_name: data.display_name, password: data.password }),
    onSuccess: async (created) => {
      reset()
      setShowCreate(false)
      setSearch(created.email)
      setPage(1)
      await queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
  const tierChange = useMutation({
    mutationFn: ({ userId, tierLevel }: { userId: string; tierLevel: 0 | 1 | 2 | 3 }) => api.updateAdminUserTier(userId, tierLevel),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })
  const userDeletion = useMutation({
    mutationFn: api.deleteAdminUser,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['admin', 'users'] })
    },
  })

  const updateTier = (user: AdminUserListItem, tierLevel: 0 | 1 | 2 | 3) => {
    const option = tierOptions.find((item) => item.value === tierLevel)
    if (window.confirm(`Change ${user.email} to ${option?.label ?? `Tier ${tierLevel}`}?`)) tierChange.mutate({ userId: user.id, tierLevel })
  }

  const removeUser = (user: AdminUserListItem) => {
    if (window.confirm(`Delete ${user.email}? Their access and active sessions will be revoked and their personal profile will be anonymized. Their existing case contributions will remain attributed to “Deleted user.”`)) userDeletion.mutate(user.id)
  }

  return <div>
    <AdminHeading title="Users" description="Search accounts by email, username, or display name and manage their tier." action={<button type="button" onClick={() => { createAdmin.reset(); setShowCreate((visible) => !visible) }} className="primary-button w-auto px-4 text-xs">{showCreate ? <X size={15}/> : <UserPlus size={15}/>} {showCreate ? 'Cancel' : 'Create administrator'}</button>}/>
    {showCreate && <form className="card mt-7 p-5 sm:p-6" onSubmit={handleSubmit((data) => createAdmin.mutate(data))}>
      <div><p className="eyebrow">Tier 0 account</p><h2 className="section-title mt-2">Create administrator</h2><p className="mt-2 text-sm text-secondary">This account receives full administrative access immediately. Share the temporary password securely.</p></div>
      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <AdminField label="Email" error={errors.email?.message}><input className="field mt-2" type="email" autoComplete="off" placeholder="admin@example.com" {...register('email')}/></AdminField>
        <AdminField label="Username" error={errors.username?.message}><input className="field mt-2" autoComplete="off" placeholder="case_admin" {...register('username')}/></AdminField>
        <AdminField label="Display name" error={errors.display_name?.message}><input className="field mt-2" autoComplete="off" placeholder="Case Administrator" {...register('display_name')}/></AdminField>
        <div className="hidden sm:block"/>
        <AdminField label="Temporary password" error={errors.password?.message}><input className="field mt-2" type="password" autoComplete="new-password" placeholder="8+ characters" {...register('password')}/></AdminField>
        <AdminField label="Confirm password" error={errors.confirm_password?.message}><input className="field mt-2" type="password" autoComplete="new-password" placeholder="Repeat password" {...register('confirm_password')}/></AdminField>
      </div>
      {createAdmin.error && <ErrorBanner error={createAdmin.error} fallback="Could not create the administrator"/>}
      <div className="mt-6 flex justify-end"><button type="submit" disabled={createAdmin.isPending} className="primary-button w-auto px-5 text-xs"><UserPlus size={15}/>{createAdmin.isPending ? 'Creating…' : 'Create administrator'}</button></div>
    </form>}
    <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1) }} placeholder="Search by email, username, or name"/>
    {tierChange.error && <ErrorBanner error={tierChange.error} fallback="Could not update the user tier"/>}
    {userDeletion.error && <ErrorBanner error={userDeletion.error} fallback="Could not delete the user"/>}
    {users.isLoading ? <Loading/> : users.data?.items.length ? <div className="mt-6 space-y-3">{users.data.items.map((user) => <article key={user.id} className="card p-5 sm:flex sm:items-center sm:justify-between sm:gap-6">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2"><h2 className="truncate text-sm font-semibold text-primary">{user.display_name}</h2>{user.is_admin && <StatusBadge tone="success">Admin</StatusBadge>}{user.moderation_status === 'locked_pending_review' ? <StatusBadge tone="danger">Locked pending review</StatusBadge> : !user.is_active && <StatusBadge tone="danger">Inactive</StatusBadge>}</div>
        <p className="mt-1 break-all text-xs text-secondary">{user.email}</p>
        <p className="metadata mt-2">@{user.username} · {user.case_count} {user.case_count === 1 ? 'case' : 'cases'} · Joined {new Date(user.created_at).toLocaleDateString()}</p>
      </div>
      <div className="mt-4 shrink-0 sm:mt-0">
        <label className="block text-[10px] font-semibold uppercase tracking-[.12em] text-muted">Tier
          <select value={user.tier_level} disabled={user.id === currentUser.data?.id || (tierChange.isPending && tierChange.variables?.userId === user.id)} onChange={(event) => updateTier(user, Number(event.target.value) as 0 | 1 | 2 | 3)} className="field mt-2 min-w-56 text-xs">
            {tierOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        {user.id === currentUser.data?.id ? <span className="mt-2 block text-[10px] text-muted">Current administrator cannot be deleted</span> : <button type="button" onClick={() => removeUser(user)} disabled={userDeletion.isPending && userDeletion.variables === user.id} className="danger-button mt-3 w-full text-xs"><Trash2 size={14}/>{userDeletion.isPending && userDeletion.variables === user.id ? 'Deleting…' : 'Delete user'}</button>}
      </div>
    </article>)}</div> : <Empty text="No users match this search."/>}
    {users.data && <Pagination page={users.data.page} totalPages={users.data.total_pages} hasPrevious={users.data.has_previous} hasNext={users.data.has_next} onPage={setPage}/>} 
  </div>
}

export function AdminCasesPage() {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const query = useDebouncedValue(search)
  const cases = useQuery({ queryKey: ['admin', 'cases', query, page], queryFn: () => api.adminCases(query, page) })
  const deletion = useMutation({
    mutationFn: api.deleteCase,
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['admin', 'cases'] }),
        queryClient.invalidateQueries({ queryKey: ['cases'] }),
      ])
    },
  })

  const remove = (item: AdminCaseListItem) => {
    if (window.confirm(`Permanently delete “${item.title}” and all of its case data? This cannot be undone.`)) deletion.mutate(item.id)
  }

  return <div>
    <AdminHeading title="Cases" description="Search by owner email, username, display name, or case title. Open or permanently delete a case."/>
    <SearchField value={search} onChange={(value) => { setSearch(value); setPage(1) }} placeholder="Search by case owner or title"/>
    {deletion.error && <ErrorBanner error={deletion.error} fallback="Could not delete the case"/>}
    {cases.isLoading ? <Loading/> : cases.data?.items.length ? <div className="mt-6 space-y-3">{cases.data.items.map((item) => <CaseRow key={item.id} item={item} deleting={deletion.isPending && deletion.variables === item.id} onDelete={() => remove(item)}/>)}</div> : <Empty text="No cases match this search."/>}
    {cases.data && <Pagination page={cases.data.page} totalPages={cases.data.total_pages} hasPrevious={cases.data.has_previous} hasNext={cases.data.has_next} onPage={setPage}/>} 
  </div>
}

function AdminHeading({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><PageHeader eyebrow="Administration" title={title} description={description}/><div className="flex flex-wrap items-center gap-3"><StatusBadge tone="success"><Shield size={14}/> Admin access</StatusBadge>{action}</div></div>
}

function AdminField({ label, error, children }: { label: string; error?: string; children: ReactNode }) {
  return <label className="block text-xs font-semibold text-primary">{label}{children}{error && <span className="mt-1 block font-normal text-danger-text">{error}</span>}</label>
}

function SearchField({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="relative mt-7 block max-w-xl"><Search className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-muted" size={17}/><span className="sr-only">{placeholder}</span><input value={value} onChange={(event) => onChange(event.target.value)} className="field pl-11" placeholder={placeholder}/></label>
}

function CaseRow({ item, deleting, onDelete }: { item: AdminCaseListItem; deleting: boolean; onDelete: () => void }) {
  return <article className="card overflow-hidden sm:flex sm:min-h-36">
    <img src={item.cover_image_url || '/case-banner.png'} alt="" className="h-36 w-full object-cover sm:h-auto sm:w-52"/>
    <div className="flex min-w-0 flex-1 flex-col gap-5 p-5 sm:flex-row sm:items-center sm:justify-between">
      <div className="min-w-0"><div className="flex flex-wrap gap-2"><StatusBadge>{item.status}</StatusBadge><StatusBadge>{item.privacy}</StatusBadge><StatusBadge tone="ai">{item.ai_research_status.replaceAll('_', ' ')}</StatusBadge></div><h2 className="section-title mt-3 truncate">{item.title}</h2><p className="mt-2 truncate text-xs text-secondary">Owned by <span className="font-semibold text-primary">{item.owner_display_name}</span> · {item.owner_email}</p><p className="metadata mt-2 text-[10px]">@{item.owner_username} · Created {new Date(item.created_at).toLocaleDateString()}</p></div>
      <div className="flex shrink-0 gap-2"><Link to={`/cases/${item.id}`} className="secondary-button text-xs"><ExternalLink size={15}/> Open</Link><button type="button" onClick={onDelete} disabled={deleting} className="danger-button text-xs"><Trash2 size={15}/>{deleting ? 'Deleting…' : 'Delete'}</button></div>
    </div>
  </article>
}

function Pagination({ page, totalPages, hasPrevious, hasNext, onPage }: { page: number; totalPages: number; hasPrevious: boolean; hasNext: boolean; onPage: (page: number) => void }) {
  if (totalPages <= 1) return null
  return <nav className="mt-7 flex items-center justify-between gap-4" aria-label="Admin results pages"><button type="button" disabled={!hasPrevious} onClick={() => onPage(page - 1)} className="secondary-button text-xs"><ChevronLeft size={15}/> Previous</button><span className="metadata">Page {page} of {totalPages}</span><button type="button" disabled={!hasNext} onClick={() => onPage(page + 1)} className="secondary-button text-xs">Next <ChevronRight size={15}/></button></nav>
}

function ErrorBanner({ error, fallback }: { error: Error; fallback: string }) {
  return <p role="alert" className="error-banner mt-6">{error instanceof ApiError ? error.message : fallback}</p>
}

function Loading() {
  return <div className="grid min-h-64 place-items-center"><Sparkles className="animate-pulse text-accent"/></div>
}

function Empty({ text }: { text: string }) {
  return <div className="card mt-8 p-10 text-center"><UserCog className="mx-auto text-muted"/><p className="mt-3 text-sm text-muted">{text}</p></div>
}

export function AdminLandingPage() {
  return <div><AdminHeading title="Admin workspace" description="Manage users, subscription tiers, cases, and reports."/><div className="mt-8 grid gap-4 sm:grid-cols-3"><Link to="/admin/users" className="card p-6 transition hover:border-accent/40"><Users className="text-accent"/><h2 className="section-title mt-5">Users</h2><p className="mt-2 text-sm text-secondary">Search accounts and adjust tier access.</p></Link><Link to="/admin/cases" className="card p-6 transition hover:border-accent/40"><Shield className="text-accent"/><h2 className="section-title mt-5">Cases</h2><p className="mt-2 text-sm text-secondary">Search case owners and remove cases.</p></Link><Link to="/admin/reports" className="card p-6 transition hover:border-accent/40"><Flag className="text-accent"/><h2 className="section-title mt-5">Reports</h2><p className="mt-2 text-sm text-secondary">Review flags and protect the community.</p></Link></div></div>
}
