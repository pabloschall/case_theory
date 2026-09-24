import { Link } from 'react-router'
import { APP_NAME } from '../config/brand'

export function Brand({ light = false, to = '/', name = APP_NAME }: { light?: boolean; to?: string; name?: string }) {
  return <Link to={to} className={`inline-flex items-center gap-3 font-display text-[30px] font-semibold leading-none tracking-[0.16em] ${light ? 'text-primary' : 'text-primary'}`} aria-label={`${name} home`}><span className="editorial-rule w-7" aria-hidden="true"/>{name}</Link>
}
