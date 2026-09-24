import { ArrowRight, LogIn, Search, UserPlus, Volume2, VolumeX } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { Brand } from '../../components/Brand'

export function LandingPage() {
  const audioRef = useRef<HTMLAudioElement>(null)
  const [soundPlaying, setSoundPlaying] = useState(false)

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

  return <main className="relative min-h-dvh overflow-hidden bg-background text-primary">
    <audio ref={audioRef} src="/landing-1.mp3" preload="auto" onPlay={() => setSoundPlaying(true)} onPause={() => setSoundPlaying(false)} onEnded={() => setSoundPlaying(false)}/>
    <img src="/landing-background.png" alt="Misty mountain lake at dusk" className="absolute inset-0 size-full object-cover object-center"/>
    <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(4,8,12,.40)_0%,rgba(4,8,12,.12)_35%,rgba(4,8,12,.48)_68%,rgba(4,8,12,.92)_100%)]"/>
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_20%,transparent_0%,rgba(4,8,12,.30)_72%)]"/>

    <div className="relative z-10 mx-auto flex min-h-dvh max-w-7xl flex-col px-5 pb-[max(2rem,env(safe-area-inset-bottom))] pt-6 sm:px-8 lg:px-12">
      <header className="flex items-center justify-between">
        <Brand light/>
        <div className="flex items-center gap-2">
          <button type="button" onClick={toggleSound} className="ghost-button size-11 border border-white/10 bg-black/10 px-0 text-primary backdrop-blur-sm" aria-label={soundPlaying ? 'Pause soundtrack' : 'Play soundtrack'} title={soundPlaying ? 'Pause soundtrack' : 'Play soundtrack'}>{soundPlaying ? <Volume2 size={16}/> : <VolumeX size={16}/>}</button>
          <Link to="/login" className="ghost-button border border-white/10 bg-black/10 text-xs text-primary backdrop-blur-sm sm:hidden"><LogIn size={15}/> Login</Link>
          <nav className="hidden items-center gap-2 sm:flex" aria-label="Account">
            <Link to="/login" className="secondary-button border-white/20 bg-black/10 px-5 text-xs backdrop-blur-sm">Login</Link>
            <Link to="/register" className="primary-button px-5 text-xs">Sign up</Link>
          </nav>
        </div>
      </header>

      <section className="mt-16 max-w-3xl sm:mt-24 lg:mt-28">
        <div className="editorial-rule w-14"/>
        <h1 className="mt-6 font-display text-[46px] font-semibold leading-[.96] tracking-[-.025em] text-primary sm:text-6xl lg:text-7xl">Real People, Real Cases.<br/><span className="text-accent">A Clear Picture.</span></h1>
        <p className="mt-6 text-[15px] font-medium tracking-[.04em] text-secondary sm:text-lg">Discuss. Share. Investigate together.</p>
      </section>

      <section className="mt-auto max-w-xl pt-16">
        <p className="max-w-md text-sm leading-6 text-secondary">Explore public cases through sourced overviews and timelines, or join the workspace to follow investigations and contribute research.</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          <Link to="/login" className="primary-button px-5"><LogIn size={16}/> Login</Link>
          <Link to="/register" className="secondary-button border-white/20 bg-black/15 px-5 backdrop-blur-sm"><UserPlus size={16}/> Sign up</Link>
          <Link to="/cases" className="ghost-button min-h-11 border border-white/10 bg-black/10 px-5 text-primary backdrop-blur-sm"><Search size={16}/> Continue as guest <ArrowRight size={14}/></Link>
        </div>
      </section>
    </div>
  </main>
}
