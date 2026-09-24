import { useMutation, useQuery } from '@tanstack/react-query'
import { ArrowRight, Clock3, LockKeyhole, UserPlus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { PageHeader } from '../../components/ui/Visual'
import { queryClient } from '../../lib/query'
import { ApiError, api } from '../../services/api'

export function InvitationPage() {
  const { token = '' } = useParams()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [autoAcceptStarted, setAutoAcceptStarted] = useState(false)
  const invitation = useQuery({ queryKey: ['invitation', token], queryFn: () => api.invitation(token), retry: false, enabled: Boolean(token) })
  const currentUser = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser, retry: false })
  const accept = useMutation({
    mutationFn: () => api.acceptInvitation(token),
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ['cases', 'following'] })
      navigate(`/cases/${result.case_id}`, { replace: true })
    },
  })
  useEffect(() => {
    if (searchParams.get('accept') === '1' && currentUser.data && invitation.data?.is_available && !autoAcceptStarted) {
      setAutoAcceptStarted(true)
      accept.mutate()
    }
  }, [accept, autoAcceptStarted, currentUser.data, invitation.data, searchParams])
  if (invitation.isLoading) return <div className="grid min-h-[65vh] place-items-center"><p className="eyebrow animate-pulse text-accent">Opening invitation</p></div>
  if (invitation.isError || !invitation.data) return <div className="mx-auto max-w-xl"><PageHeader eyebrow="Collaboration" title="Invitation unavailable" description="This invitation link is invalid or no longer exists."/><Link to="/cases" className="secondary-button mt-6 w-fit">Browse public cases</Link></div>
  const item = invitation.data
  const next = `/invite/${token}?accept=1`
  return <div className="mx-auto max-w-2xl py-6 sm:py-12"><section className="surface overflow-hidden"><div className="border-b border-accent/20 bg-accent-muted px-6 py-4"><p className="eyebrow flex items-center gap-2 text-accent"><UserPlus size={14}/> Collaboration invitation</p></div><div className="p-6 sm:p-10"><p className="text-sm text-secondary"><strong className="text-primary">{item.inviter_name}</strong> invited you to collaborate on</p><h1 className="page-title mt-3">{item.case_title}</h1><div className="mt-6 flex flex-wrap gap-3"><span className="status-badge"><UserPlus size={12}/> Contributor</span><span className="status-badge"><LockKeyhole size={12}/> Account required</span></div><p className="mt-6 text-sm leading-6 text-secondary">Collaborators can open the case workspace and contribute research. After you join, this case will be added to My Desk.</p><p className="mt-4 flex items-center gap-2 text-xs text-muted"><Clock3 size={14}/> Invitation expires {new Date(item.expires_at).toLocaleString()}</p>{!item.is_available ? <div className="error-banner mt-6">This invitation has expired or has already been accepted.</div> : currentUser.data ? <><button type="button" disabled={accept.isPending || autoAcceptStarted} onClick={() => accept.mutate()} className="primary-button mt-7"><UserPlus size={16}/>{accept.isPending || autoAcceptStarted ? 'Joining case…' : 'Accept invitation'}</button>{accept.error && <p role="alert" className="error-banner mt-4">{accept.error instanceof ApiError ? accept.error.message : 'The invitation could not be accepted.'}</p>}</> : <div className="mt-7 grid gap-3 sm:grid-cols-2"><Link to={`/register?next=${encodeURIComponent(next)}`} className="primary-button">Create account <ArrowRight size={16}/></Link><Link to={`/login?next=${encodeURIComponent(next)}`} className="secondary-button">Sign in</Link></div>}</div></section></div>
}
