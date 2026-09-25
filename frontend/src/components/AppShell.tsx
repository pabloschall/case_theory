import { useQuery } from '@tanstack/react-query'
import { Archive, Flag, Home, LogIn, Menu, MessageCircle, Plus, Search, Telescope, UserPlus, UserRound, Users, Volume2, VolumeX, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, Outlet, useLocation } from 'react-router'
import { api } from '../services/api'
import { useUiStore } from '../state/ui'
import { Brand } from './Brand'

const workspaceNavigation = [
  { to: '/cases', label: 'Case Directory', icon: Search },
  { to: '/research', label: 'Research', icon: Telescope },
  { to: '/desk', label: 'My Desk', icon: Home },
  { to: '/my-cases', label: 'My Cases', icon: Archive },
  { to: '/messages', label: 'Messenger', icon: MessageCircle },
]

const adminNavigation = [
  { to: '/admin/users', label: 'Users', icon: Users },
  { to: '/admin/cases', label: 'Cases', icon: Archive },
  { to: '/admin/reports', label: 'Reports', icon: Flag },
]

export function AppShell() {
  const greetingAudioRef = useRef<HTMLAudioElement>(null)
  const [greetingVisible, setGreetingVisible] = useState(false)
  const [greetingPlaying, setGreetingPlaying] = useState(false)
  const { navigationOpen, setNavigationOpen } = useUiStore()
  const location = useLocation()
  const { data: currentUser } = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser, retry: false })
  const authenticated = Boolean(currentUser)
  const canAccessAdmin = currentUser?.permissions.includes('admin.access') ?? false
  const canMessage = currentUser?.permissions.includes('messaging.use') ?? false
  const { data: unreadMessages } = useQuery({ queryKey: ['messages', 'unread'], queryFn: api.unreadMessages, enabled: canMessage, refetchInterval: 5000 })
  const showMessengerDot = unreadMessages?.has_unread ?? false
  const authenticatedNavigation = canAccessAdmin ? adminNavigation : workspaceNavigation
  const primaryNavigation = authenticated ? authenticatedNavigation : workspaceNavigation.slice(0, 1)
  const mobileNavigation = authenticated
    ? [...primaryNavigation, { to: '/profile', label: 'Profile', icon: UserRound }]
    : [...primaryNavigation, { to: '/login', label: 'Login', icon: LogIn }, { to: '/register', label: 'Sign up', icon: UserPlus }]

  useEffect(() => {
    if (!authenticated || sessionStorage.getItem('play-login-greeting') !== 'true') return
    sessionStorage.removeItem('play-login-greeting')
    const audio = greetingAudioRef.current
    if (!audio) return
    audio.volume = 0.32
    setGreetingVisible(true)
    void audio.play().catch(() => setGreetingPlaying(false))
  }, [authenticated])

  const toggleGreeting = () => {
    const audio = greetingAudioRef.current
    if (!audio) return
    if (audio.paused) void audio.play().catch(() => setGreetingPlaying(false))
    else audio.pause()
  }

  const isActive = (to: string) => to === '/cases'
    ? location.pathname.startsWith('/cases')
    : location.pathname.startsWith(to)

  return <div className="min-h-dvh bg-transparent text-primary">
    <audio ref={greetingAudioRef} src="/greeting-female-trimmed.mp3" preload="auto" onPlay={() => setGreetingPlaying(true)} onPause={() => setGreetingPlaying(false)} onEnded={() => { setGreetingPlaying(false); setGreetingVisible(false) }}/>
    <header className="sticky top-0 z-30 border-b border-subtle bg-background/95 backdrop-blur-xl">
      <div className="mx-auto flex h-[72px] max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <Brand to={canAccessAdmin ? '/admin/users' : '/cases'} />
        <nav className="hidden items-center gap-8 md:flex" aria-label="Workspace">
          {primaryNavigation.map(({ to, label }) => <Link key={to} to={to} className={`relative py-7 text-[11px] font-semibold uppercase tracking-[.14em] transition duration-200 ${isActive(to) ? 'text-accent after:absolute after:inset-x-0 after:bottom-0 after:h-px after:bg-accent' : 'text-muted hover:text-primary'}`}>{label}{to === '/messages' && showMessengerDot && <span aria-label="Unread messages" className="absolute right-[-9px] top-[22px] size-2 rounded-full bg-red-500"/>}</Link>)}
        </nav>
        <div className="flex items-center gap-2">
          {greetingVisible && <button type="button" onClick={toggleGreeting} className="ghost-button size-11 px-0" aria-label={greetingPlaying ? 'Pause greeting' : 'Play greeting'} title={greetingPlaying ? 'Pause greeting' : 'Play greeting'}>{greetingPlaying ? <Volume2 size={17}/> : <VolumeX size={17}/>}</button>}
          {authenticated ? <>{!canAccessAdmin && <Link to="/cases/new" className="secondary-button hidden text-xs text-accent md:flex"><Plus size={15}/> New case</Link>}<Link to="/profile" className="ghost-button hidden size-11 px-0 md:grid" aria-label="Profile"><UserRound size={18}/></Link></> : <div className="hidden items-center gap-2 md:flex"><Link to="/login" className="ghost-button text-xs">Login</Link><Link to="/register" className="primary-button min-h-10 px-4 text-xs">Sign up</Link></div>}
          <button onClick={() => setNavigationOpen(!navigationOpen)} className="ghost-button size-11 px-0 md:hidden" aria-label="Toggle navigation">{navigationOpen ? <X size={20}/> : <Menu size={20}/>}</button>
        </div>
      </div>
      {navigationOpen && <nav className="border-t border-subtle bg-surface p-4 md:hidden" aria-label="Mobile workspace">{mobileNavigation.map(({to,label}) => <Link onClick={() => setNavigationOpen(false)} key={to} to={to} className={`flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-semibold ${isActive(to) ? 'bg-accent-muted text-accent' : 'text-primary hover:bg-white/5'}`}>{label}{to === '/messages' && showMessengerDot && <span aria-label="Unread messages" className="size-2 rounded-full bg-red-500"/>}</Link>)}</nav>}
    </header>
    <main className="mx-auto max-w-7xl px-4 pb-28 pt-6 sm:px-6 lg:px-8 lg:pb-12"><Outlet /></main>
    <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-subtle bg-background/95 px-2 pb-[max(.45rem,env(safe-area-inset-bottom))] pt-2 backdrop-blur-xl md:hidden" aria-label="Primary">
      <div className="mx-auto grid max-w-md" style={{ gridTemplateColumns: `repeat(${mobileNavigation.length}, minmax(0, 1fr))` }}>{mobileNavigation.map(({to,label,icon:Icon}) => <Link key={to} to={to} className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-lg text-[10px] font-medium transition duration-200 ${isActive(to) ? 'text-accent' : 'text-muted'}`}><span className="relative"><Icon size={18}/>{to === '/messages' && showMessengerDot && <span aria-label="Unread messages" className="absolute -right-2 -top-1 size-2 rounded-full bg-red-500"/>}</span>{label}</Link>)}</div>
    </nav>
  </div>
}
