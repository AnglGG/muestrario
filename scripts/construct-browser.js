(() => {
  const original = new URL('https://www.tobiadonadon.com/projects/construct/design')
  const mirror = new URL('__CONSTRUCT_MIRROR__', location.origin)
  const publicPages = new Set(['', '/mcp'])
  const nativeFetch = window.fetch.bind(window)
  const stats = new URL('stats.json', mirror)
  const internalLink = 'a[href^="/"]:not([href^="//"])'
  const rewrittenLinks = new WeakSet()

  window.addEventListener('cd:auth', event => event.stopImmediatePropagation(), true)

  function rewriteLink(link) {
    const destination = new URL(link.getAttribute('href'), original)
    const suffix = destination.pathname.slice(original.pathname.length)
    if (destination.pathname.startsWith(original.pathname) && publicPages.has(suffix)) {
      const local = new URL(suffix ? suffix.slice(1) + '/' : '', mirror)
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
    }
    return Promise.resolve(Response.json({}, { status: 401 }))
  }

  window.addEventListener('click', event => {
    if (!(event.target instanceof Element)) return
    const link = event.target.closest('a[href]')
    if (link?.matches(internalLink)) rewriteLink(link)
    if (link && rewrittenLinks.has(link)) {
      const destination = new URL(link.href)
      const normalClick = !(event.altKey || event.ctrlKey || event.metaKey || event.shiftKey || event.button)
      const catalogueTab = destination.origin + destination.pathname === mirror.href &&
        location.pathname === mirror.pathname && link.closest('nav[aria-label="Main"]')
      if (!(catalogueTab && normalClick)) {
        event.stopPropagation()
      }
    }
  }, true)
})()
