import { useEffect } from 'react'

const SITE_ORIGIN = 'https://case-researcher.com'

type SeoProps = {
  title: string
  description: string
  path: string
  image?: string | null
  noindex?: boolean
}

export function Seo({ title, description, path, image, noindex = false }: SeoProps) {
  useEffect(() => {
    const originalTitle = document.title
    const restore: Array<() => void> = []
    const url = `${SITE_ORIGIN}${path}`

    const setMeta = (attribute: 'name' | 'property', key: string, value: string) => {
      let element = document.querySelector<HTMLMetaElement>(`meta[${attribute}="${key}"]`)
      const created = !element
      if (!element) {
        element = document.createElement('meta')
        element.setAttribute(attribute, key)
        document.head.appendChild(element)
      }
      const previous = element.getAttribute('content')
      element.setAttribute('content', value)
      restore.push(() => {
        if (created) element.remove()
        else if (previous === null) element.removeAttribute('content')
        else element.setAttribute('content', previous)
      })
    }

    document.title = title
    setMeta('name', 'description', description)
    setMeta('property', 'og:title', title)
    setMeta('property', 'og:description', description)
    setMeta('property', 'og:url', url)
    setMeta('name', 'twitter:card', 'summary_large_image')
    if (image) setMeta('property', 'og:image', image)
    if (noindex) setMeta('name', 'robots', 'noindex, nofollow')

    let canonical = document.querySelector<HTMLLinkElement>('link[rel="canonical"]')
    const createdCanonical = !canonical
    if (!canonical) {
      canonical = document.createElement('link')
      canonical.rel = 'canonical'
      document.head.appendChild(canonical)
    }
    const previousHref = canonical.getAttribute('href')
    canonical.href = url
    restore.push(() => {
      if (createdCanonical) canonical.remove()
      else if (previousHref === null) canonical.removeAttribute('href')
      else canonical.setAttribute('href', previousHref)
    })

    return () => {
      document.title = originalTitle
      restore.reverse().forEach((undo) => undo())
    }
  }, [title, description, path, image, noindex])

  return null
}
