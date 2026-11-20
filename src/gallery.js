const snapshot = JSON.parse(document.querySelector('#snapshot').textContent)
const library = createLibrary(snapshot)
const $ = id => document.getElementById(id)
const mobile = matchMedia('(max-width: 879px)')
const pageSize = 24
let type = ''
let offset = 0
let listed = []
let renderedDetail = null
let returningToCatalogue = false

const newElement = (tag, text, className) => {
  const element = document.createElement(tag)
  if (text) element.textContent = text
  if (className) element.className = className
  return element
}

function itemLink(entry, className, text = entry.name) {
  const link = newElement('a', text, className)
  link.href = '#ficha/' + entry.id
  return link
}

function previewLink(entry) {
  const link = newElement('a', 'Ver vista previa', 'source')
  link.href = constructPreview(entry, location.protocol === 'file:' ? undefined : location.href)
  link.target = '_blank'
  link.rel = 'noreferrer'
  return link
}

function art(entry, large = false) {
  const swatch = newElement('span', '', large ? 'swatch detail-art' : 'swatch')
  swatch.dataset.category = entry.category
  swatch.setAttribute('aria-hidden', 'true')
  if (entry.poster) {
    const image = newElement('img')
    image.alt = ''
    image.loading = 'lazy'
    image.referrerPolicy = 'no-referrer'
    image.addEventListener('error', () => image.remove(), { once: true })
    image.src = entry.poster
    swatch.append(image)
  }
  return swatch
}

function renderCard(entry) {
  const link = itemLink(entry, 'card', '')
  const text = newElement('span')
  text.append(newElement('strong', entry.name), newElement('small', categoryLabel(entry.category) + ' · ' + types[entry.type]))
  link.dataset.id = entry.id
  link.append(art(entry), text)
  return link
}

function currentEntry() {
  const id = location.hash.startsWith('#ficha/') ? location.hash.slice(7) : null
  return id ? library.get(id, true) : null
}

function addTags(container, tags) {
  if (!tags.length) return
  const list = newElement('ul', '', 'tags')
  list.setAttribute('aria-label', 'Características')
  list.append(...tags.map(tag => newElement('li', tag)))
  container.append(list)
}

function addRelated(container, label, entries) {
  if (!entries.length) return
  const links = newElement('div', '', 'related')
  links.append(...entries.map(entry => itemLink(entry)))
  container.append(newElement('h3', label), links)
}

const demoStyles = `
  *, *::before, *::after { box-sizing: border-box; }
  html { color-scheme: light; }
  body { min-height: calc(100dvh - 24px); display: grid; align-content: center; padding: 0 1px; margin: 12px; color: #222b23; background: #eaf2e3; font: 15px/1.42 system-ui, sans-serif; }
  button { font: inherit; padding: 7px; border: 1px solid #56866b; background: #f8fbf5; border-radius: 5px; cursor: pointer; color: inherit; }
  button[aria-disabled="true"] { cursor: wait; }
  :focus-visible { outline: 2px solid #226040; outline-offset: 2px; }
`

function renderRecipe(entry, container) {
  const frame = newElement('iframe')
  frame.title = 'Demostración de ' + entry.name
  frame.setAttribute('sandbox', 'allow-scripts allow-forms')
  frame.srcdoc = '<!doctype html><html lang="es"><meta charset="utf-8"><style>' + demoStyles + '</style><body>' + entry.code
  container.append(frame, newElement('p', entry.controls, 'meta'), newElement('p', entry.usage))

  const disclosure = newElement('details')
  const code = newElement('textarea')
  code.readOnly = true
  code.spellcheck = false
  code.setAttribute('aria-label', 'Código HTML de ' + entry.name)
  code.value = entry.code
  const copy = newElement('button', 'Copiar código', 'copy')
  const status = newElement('p', '', 'meta')
  status.setAttribute('role', 'status')
  status.hidden = true
  copy.onclick = async () => {
    try {
      await navigator.clipboard.writeText(entry.code)
      status.textContent = 'Código copiado.'
    } catch {
      code.focus()
      code.select()
      status.textContent = 'Código seleccionado. Pulsa ⌘C o Ctrl+C para copiar.'
    }
    status.hidden = false
  }
  disclosure.append(newElement('summary', 'Ver código HTML'), code, copy, status)
  container.append(disclosure)
  addRelated(container, 'Referencias de Construct', entry.references)
}

function renderDetail(entry) {
  const container = $('detail')
  container.replaceChildren()
  if (!entry) {
    container.append(newElement('h2', 'Explora una ficha'), newElement('p', 'Elige un resultado para ver sus características y referencias.'))
    return
  }

  if (entry.type !== 'recipe') container.append(art(entry, true))
  const title = newElement('h2', entry.name)
  title.tabIndex = -1
  const meta = types[entry.type] + ' · ' + categoryLabel(entry.category)
  container.append(newElement('div', meta, 'meta'), title)
  const summary = entry.summary ?? entry.description
  if (summary) {
    const description = newElement('p', summary)
    if (!entry.summary) description.lang = 'en'
    container.append(description)
  }
  if (entry.type === 'recipe') {
    renderRecipe(entry, container)
  } else {
    addTags(container, entry.tags)
    if (entry.controls?.length) container.append(newElement('p', 'Controles: ' + entry.controls.join(', '), 'meta'))
    container.append(previewLink(entry))
    if (entry.originals.length) {
      addRelated(container, 'Patrones originales relacionados', entry.originals)
    } else if (entry.categoryRecipe) {
      addRelated(container, 'Patrón original de esta categoría', [entry.categoryRecipe])
    }
  }
}

function updateDetail({ focus = false } = {}) {
  const selected = currentEntry()
  $('workspace').dataset.open = String(Boolean(selected))
  for (const link of $('results').querySelectorAll('.card')) {
    if (selected?.id === link.dataset.id) link.setAttribute('aria-current', 'true')
    else link.removeAttribute('aria-current')
  }
  const detailId = selected?.id ?? listed[0]?.id ?? null
  if (renderedDetail !== detailId || !$('detail').firstChild) {
    renderDetail(selected ?? library.get(detailId, true))
    $('inspector').scrollTop = 0
    renderedDetail = detailId
  }
  if (!focus) return
  if (mobile.matches && selected) $('inspector').scrollIntoView()
  if (selected) $('detail').querySelector('h2')?.focus({ preventScroll: true })
  else if (mobile.matches) $('query').focus({ preventScroll: true })
}

function showResults() {
  const { total, items } = library.search({
    query: $('query').value, type, category: $('category').value, offset, limit: pageSize
  })
  listed = items
  const label = total === 1 ? 'ficha' : 'fichas'
  $('result-count').textContent = total + ' ' + label
  $('position').textContent = total > pageSize ? (offset + 1) + '–' + (offset + items.length) + ' de ' + total : ''
  const empty = newElement('p', 'Prueba otro término o quita un filtro.', 'empty')
  $('results').replaceChildren(...(items.length ? items.map(renderCard) : [empty]))
  $('pager').hidden = total <= pageSize
  $('previous').disabled = offset === 0
  $('next').disabled = offset + pageSize >= total
  updateDetail()
}

function populateCategories() {
  $('category').replaceChildren(new Option('Todas las categorías', ''))
  for (const group of library.listCategories(type)) {
    $('category').append(new Option(group.label + ' (' + group.count + ')', group.id))
  }
}

function returnToCatalogue() {
  if (returningToCatalogue) return
  if (history.state?.fromCatalogue) {
    returningToCatalogue = true
    history.back()
  } else {
    history.replaceState(null, '', '#catalogo')
    updateDetail({ focus: true })
    if (mobile.matches) $('query').scrollIntoView({ block: 'center' })
  }
}

function resetFilters() {
  offset = 0
  if (currentEntry()) returnToCatalogue()
  showResults()
}

const options = [
  ['', 'Todo'], ['component', 'Componentes'], ['app', 'Apps'],
  ['website', 'Webs'], ['recipe', 'Patrones originales']
]
for (const [value, label] of options) {
  const count = library.search({ type: value, limit: 0 }).total
  const button = newElement('button', label, 'type')
  button.type = 'button'
  button.setAttribute('aria-pressed', String(!value))
  button.append(newElement('span', String(count)))
  button.onclick = () => {
    type = value
    for (const other of $('types').children) other.setAttribute('aria-pressed', String(other === button))
    populateCategories()
    resetFilters()
  }
  $('types').append(button)
}

$('filters').onsubmit = event => event.preventDefault()
$('query').addEventListener('input', resetFilters)
$('category').addEventListener('change', resetFilters)
$('workspace').addEventListener('click', event => {
  const link = event.target.closest('a[href^="#ficha/"]')
  if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  if (currentEntry()) {
    history.replaceState(history.state, '', link.hash)
  } else {
    history.pushState({ fromCatalogue: true }, '', link.hash)
  }
  updateDetail({ focus: true })
})

$('back').onclick = returnToCatalogue
document.querySelector('.wordmark').addEventListener('click', event => {
  if (!currentEntry() || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return
  event.preventDefault()
  returnToCatalogue()
})
for (const [id, change] of [['previous', -1], ['next', 1]]) {
  $(id).onclick = () => {
    offset += change * pageSize
    showResults()
    const first = $('results').querySelector('.card')
    first?.focus()
  }
}
window.addEventListener('hashchange', () => {
  returningToCatalogue = false
  const connecting = location.hash === '#mcp'
  if (connecting) $('mcp').open = true
  updateDetail({ focus: !connecting })
})
if (location.hash === '#mcp') $('mcp').open = true
populateCategories()
showResults()
