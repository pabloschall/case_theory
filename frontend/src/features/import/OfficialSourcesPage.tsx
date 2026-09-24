import { Building2, ExternalLink, FileSearch2 } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { PageHeader, UpgradeButton } from '../../components/ui/Visual'
import { APP_NAME } from '../../config/brand'
import { api } from '../../services/api'

export function OfficialSourcesPage() {
  const { data: user } = useQuery({ queryKey: ['current-user'], queryFn: api.currentUser })
  const canImport = user?.permissions.includes('case.import') ?? false
  return <div className="mx-auto max-w-4xl">
    <PageHeader eyebrow="Source discovery" title="Research" description="Explore official public records and turn selected source material into a private case draft."/>
    <div className="mt-8 flex items-end justify-between gap-4 border-b border-subtle pb-3"><div><p className="eyebrow text-accent">Integrations</p><h2 className="section-title mt-1">Official Sources</h2></div><span className="metadata">More sources coming later</span></div>
    <div className="mt-4 grid gap-4 sm:grid-cols-2">
      <article className="card relative overflow-hidden p-6">
        <div className="flex items-start justify-between gap-4"><span className="grid size-11 place-items-center rounded-lg border border-blue/25 bg-blue-muted text-blue"><Building2 size={21}/></span><span className="eyebrow text-blue">Official source</span></div>
        <h2 className="section-title mt-6">FBI</h2>
        <p className="mt-1 text-xs font-semibold text-secondary">Federal Bureau of Investigation</p>
        <p className="mt-4 text-sm leading-6 text-secondary">Browse publicly available wanted, missing-person, and seeking-information records.</p>
        {canImport ? <Link to="/fbi" className="primary-button mt-6 w-fit px-4"><FileSearch2 size={16}/> Browse FBI Cases</Link> : <div className="mt-6"><UpgradeButton className="secondary-button w-fit text-xs" description="Official source discovery and imports are available on the Investigator plan."><FileSearch2 size={16}/> Browse FBI Cases</UpgradeButton></div>}
      </article>
      <article className="card border-dashed p-6 opacity-70"><span className="grid size-11 place-items-center rounded-lg bg-tertiary text-muted"><ExternalLink size={20}/></span><h2 className="section-title mt-6">More sources</h2><p className="mt-3 text-sm leading-6 text-muted">NamUs, state cold-case databases, and local agencies can be added through the same source-provider system.</p></article>
    </div>
    <p className="mt-6 text-xs leading-5 text-muted">{APP_NAME} is an independent platform and is not affiliated with or endorsed by the agencies listed here.</p>
  </div>
}
