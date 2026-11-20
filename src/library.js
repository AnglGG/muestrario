const groups = {
  Drag: ['Arrastre', 'arrastrar gesto swipe drag'],
  Press: ['Pulsación', 'pulsar botón press click tap'],
  Hover: ['Puntero', 'hover foco puntero ratón'],
  Select: ['Selección', 'selector select elegir'],
  Type: ['Escritura', 'escribir entrada formulario type'],
  Scroll: ['Desplazamiento', 'scroll desplazamiento'],
  Loading: ['Carga', 'loading espera progreso asíncrono'],
  Shader: ['Efectos visuales', 'shader luz visual gradiente'],
  Productivity: ['Productividad', 'productivity'],
  Finance: ['Finanzas', 'finance pago dinero'],
  Health: ['Salud', 'health bienestar'],
  Travel: ['Viajes', 'travel'],
  Social: ['Social', 'comunidad'],
  Home: ['Hogar', 'home'],
  Food: ['Comida', 'food cocina'],
  Music: ['Música', 'music audio'],
  AI: ['IA', 'ai inteligencia artificial'],
  Commerce: ['Comercio', 'commerce tienda ecommerce'],
  Agency: ['Agencia', 'agency'],
  Portfolio: ['Portafolio', 'portfolio'],
  SaaS: ['SaaS', 'software'],
  Studio: ['Estudio', 'studio']
}

const types = {
  component: 'Componente',
  app: 'App',
  website: 'Web',
  recipe: 'Patrón original'
}

function words(value) {
  return value.normalize('NFD').replace(/\p{Diacritic}/gu, '')
    .toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}

const stopWords = new Set('a al con de del el en for la las los me para por que un una y and the with'.split(' '))

function includesTerm(text, term) {
  if (term.length <= 2) return (' ' + text + ' ').includes(' ' + term + ' ')
  return text.includes(term)
}

function categoryLabel(category) {
  return groups[category]?.[0] ?? category
}

function createLibrary(snapshot) {
  const entries = [
    ...snapshot.references,
    ...snapshot.recipes.map(({ code, ...entry }) => ({ ...entry, type: 'recipe' }))
  ]
  const byId = new Map(entries.map(entry => [entry.id, entry]))
  const recipesById = new Map(snapshot.recipes.map(entry => [entry.id, entry]))
  const indexed = entries.map(entry => ({
    entry,
    name: words(entry.name + ' ' + entry.id),
    labels: words([entry.category, ...(groups[entry.category] ?? []), ...entry.tags].join(' ')),
    summary: words([entry.summary, entry.description, entry.controls].flat().filter(Boolean).join(' '))
  }))

  function search({ query = '', type, category, offset = 0, limit = 24 } = {}) {
    const phrase = words(query)
    let terms = [...new Set(phrase.split(' ').filter(term => term && !stopWords.has(term)))]
    if (phrase && !terms.length) terms = [phrase]
    const matches = []
    for (const { entry, name, labels, summary } of indexed) {
      if ((type && entry.type !== type) || (category && entry.category !== category)) continue
      let score = phrase && includesTerm(name, phrase) ? 8 : 0
      const matched = terms.every(term => {
        const weight = includesTerm(name, term) ? 5
          : includesTerm(labels, term) ? 3
          : includesTerm(summary, term) ? 1
          : 0
        score += weight
        return weight > 0
      })
      if (matched) matches.push({ entry, score })
    }
    matches.sort((a, b) => b.score - a.score)
    return {
      total: matches.length,
      offset,
      items: matches.slice(offset, offset + limit).map(({ entry }) => entry)
    }
  }

  function listCategories(type) {
    const totals = new Map()
    for (const entry of entries) {
      if (type && entry.type !== type) continue
      totals.set(entry.category, (totals.get(entry.category) ?? 0) + 1)
    }
    return [...totals].map(([id, count]) => ({ id, label: categoryLabel(id), count }))
      .sort((a, b) => a.label.localeCompare(b.label, 'es'))
  }

  function get(id, includeCode = false) {
    const entry = byId.get(id)
    if (!entry) return null
    if (entry.type === 'recipe') {
      const references = entry.references.map(id => byId.get(id))
      const result = { ...entry, references }
      if (includeCode) result.code = recipesById.get(id).code
      return result
    }

    const originals = entries.filter(item => item.type === 'recipe' && item.references.includes(id))
    const categoryRecipe = entries.find(item => item.type === 'recipe' && item.category === entry.category)
    return { ...entry, originals, categoryRecipe: categoryRecipe ?? null }
  }

  return { search, get, listCategories }
}

function constructPreview(entry, base = 'https://anglgg.github.io/muestrario/') {
  const url = new URL('construct/', base)
  url.searchParams.set('kind', entry.type)
  url.searchParams.set('block', entry.id)
  return url.href
}

if (typeof module !== 'undefined') module.exports = { createLibrary, categoryLabel, constructPreview, types }
