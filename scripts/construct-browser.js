(() => {
  const original = new URL('https://www.tobiadonadon.com/projects/construct/design')
  const officialAccount = new URL('/projects/construct/account?from=design', original)
  const officialJoin = new URL('/projects/construct/join', original)
  const officialPricing = new URL(original.pathname + '/pricing', original)
  const nativeFetch = window.fetch.bind(window)
  const stats = new URL('stats.json', location.href.split('?')[0].split('#')[0])
  const internalLink = 'a[href^="/"]:not([href^="//"])'
  const rewrittenLinks = new WeakSet()

  try {
    // The welcome form belongs on the original domain, like the join button.
    localStorage.setItem('cd:welcomed', '1')
  } catch {}

  function openOriginal() {
    const url = new URL(original)
    url.search = location.search
    location.assign(url)
  }

  function rewriteLink(link) {
    const destination = new URL(link.getAttribute('href'), original)
    if (destination.pathname === original.pathname) {
      const local = new URL(location.pathname, location.origin)
      local.search = destination.search
      local.hash = destination.hash
      destination.href = local.href
    }
    link.href = destination.href
    rewrittenLinks.add(link)
  }

  function rewriteLinksIn(root) {
    if (root.matches?.(internalLink)) rewriteLink(root)
    root.querySelectorAll?.(internalLink).forEach(rewriteLink)
  }

  function observeLinks() {
    rewriteLinksIn(document.body)
    new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'attributes' && record.target.matches(internalLink)) {
          rewriteLink(record.target)
        }
        record.addedNodes.forEach(rewriteLinksIn)
      }
    }).observe(document.body, { subtree: true, childList: true, attributeFilter: ['href'] })
  }

  if (document.readyState === 'loading') {
    window.addEventListener('DOMContentLoaded', observeLinks, { once: true })
  } else {
    observeLinks()
  }

  window.fetch = (input, init) => {
    const url = new URL(input instanceof Request ? input.url : input, location.href)
    if (url.origin === location.origin && url.searchParams.has('_rsc')) {
      return Promise.resolve(new Response(null, { status: 204 }))
    }
    if (url.origin !== location.origin || !url.pathname.startsWith('/api/')) {
      return nativeFetch(input, init)
    }
    switch (url.pathname) {
      case '/api/account/me':
        return Promise.resolve(Response.json({ ok: true, member: null }))
      case '/api/design/stats':
        return nativeFetch(stats)
      case '/api/design/event':
        return Promise.resolve(new Response(null, { status: 204 }))
      case '/api/design/source':
        openOriginal()
        break
    }
    return Promise.resolve(Response.json({}, { status: 401 }))
  }

  window.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return
    const link = event.target.closest('a[href]')
    if (link?.matches(internalLink)) rewriteLink(link)
    if (link && rewrittenLinks.has(link)) {
      event.stopPropagation()
      return
    }

    const button = event.target.closest('button')
    if (!button) return
    const text = button.textContent.trim().replace(/\s+/g, ' ')
    if (/^(Sign in|Save and sign in)$/i.test(text)) {
      event.preventDefault()
      event.stopPropagation()
      location.assign(officialAccount)
    } else if (/^(Get Pro|Start 7 days free)/i.test(text)) {
      event.preventDefault()
      event.stopPropagation()
      location.assign(officialPricing)
    } else if (/^(Join (?:for )?free|Join Construct Design)/i.test(text)) {
      event.preventDefault()
      event.stopPropagation()
      location.assign(officialJoin)
    }
  }, true)

  window.addEventListener('submit', event => {
    if (!event.target.querySelector('input[type="email"], input[autocomplete="one-time-code"]')) return
    event.preventDefault()
    event.stopPropagation()
    location.assign(officialAccount)
  }, true)
})()
