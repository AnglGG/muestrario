const readline = require('node:readline')
const fs = require('node:fs')
const path = require('node:path')
const catalog = require('./catalog.json')
const recipeIndex = require('./recipes/index.json')
const { createLibrary } = require('./src/library.js')

const versions = ['2025-11-25', '2025-06-18', '2025-03-26', '2024-11-05']
const readRecipe = id => fs.readFileSync(path.join(__dirname, 'recipes', id + '.html'), 'utf8')
const library = createLibrary({ ...catalog, recipes: recipeIndex.map(recipe => ({ ...recipe, code: readRecipe(recipe.id) })) })

const type = { type: 'string', enum: ['component', 'app', 'website', 'recipe'] }
const category = { type: 'string', maxLength: 80, description: 'Identificador de list_categories, por ejemplo Drag.' }
const schemas = {
  search_library: {
    description: 'Busca referencias de Construct y patrones originales por nombre, interacción o etiquetas. Usa 1–3 términos específicos, sin palabras de relleno. type=recipe filtra a patrones con código reutilizable.',
    properties: {
      query: { type: 'string', maxLength: 200 },
      type, category,
      limit: { type: 'integer', minimum: 1, maximum: 50, default: 12 },
      offset: { type: 'integer', minimum: 0, maximum: 5000, default: 0 }
    },
    call({ query, type, category, limit = 12, offset }) {
      const results = library.search({ query, type, category, limit, offset })
      const next = results.offset + results.items.length
      return { ...results, nextOffset: next < results.total ? next : null }
    }
  },
  get_entry: {
    description: 'Devuelve la ficha por id. En un patrón original, incluye instrucciones, referencias y código HTML/CSS/JS completo, salvo que includeCode sea false. En una referencia, ofrece el enlace de Construct y los patrones originales relacionados.',
    properties: {
      id: { type: 'string', minLength: 1, maxLength: 120 },
      includeCode: { type: 'boolean', default: true }
    },
    required: ['id'],
    call({ id, includeCode = true }) {
      return library.get(id, includeCode)
    }
  },
  list_categories: {
    description: 'Enumera categorías y recuentos. Los identificadores funcionan como filtros exactos en search_library.',
    properties: { type },
    call({ type }) {
      return { categories: library.listCategories(type) }
    }
  }
}

const tools = Object.entries(schemas).map(([name, definition]) => ({
  name,
  description: definition.description,
  inputSchema: {
    type: 'object',
    additionalProperties: false,
    properties: definition.properties,
    ...(definition.required ? { required: definition.required } : {})
  },
  annotations: {
    readOnlyHint: true,
    destructiveHint: false,
    idempotentHint: true,
    openWorldHint: false
  }
}))

function validate(args, definition) {
  if (!args || typeof args !== 'object' || Array.isArray(args)) return 'arguments debe ser un objeto.'
  for (const field of definition.required ?? []) {
    if (!Object.hasOwn(args, field)) return 'Falta ' + field + '.'
  }
  for (const [key, value] of Object.entries(args)) {
    const rule = Object.hasOwn(definition.properties, key) ? definition.properties[key] : null
    if (!rule) return 'Campo desconocido: ' + key
    if (rule.type === 'integer') {
      if (!Number.isInteger(value) || value < rule.minimum || value > rule.maximum) return 'Valor fuera de rango: ' + key
    } else if (typeof value !== rule.type) {
      return 'Tipo inválido: ' + key
    }
    if (rule.enum && !rule.enum.includes(value)) return 'Valor inválido: ' + key
    if (rule.type === 'string' && (value.length < (rule.minLength ?? 0) || value.length > (rule.maxLength ?? Infinity))) {
      return 'Longitud inválida: ' + key
    }
  }
  return null
}

let initialized = false
let version = versions[0]
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity })

function write(id, payload) {
  process.stdout.write(JSON.stringify({ jsonrpc: '2.0', id, ...payload }) + '\n')
}

function run(request) {
  const { method, params, id } = request
  if (method === 'initialize') {
    if (typeof params?.protocolVersion !== 'string') return { error: { code: -32602, message: 'Falta protocolVersion.' } }
    version = versions.includes(params.protocolVersion) ? params.protocolVersion : versions[0]
    return { result: {
      protocolVersion: version,
      capabilities: { tools: {} },
      serverInfo: { name: 'muestrario', version: '1.0.0' },
      instructions: 'Busca por interacción, abre la ficha elegida y adapta su patrón original a los componentes y tokens existentes del proyecto. Las referencias de Construct enlazan a la fuente.'
    } }
  }
  if (method === 'ping') return { result: {} }
  if (!initialized) return { error: { code: -32002, message: 'Servidor pendiente de inicialización.' } }
  if (method === 'tools/list') return { result: { tools } }
  if (method === 'tools/call') {
    const definition = Object.hasOwn(schemas, params?.name) ? schemas[params.name] : null
    if (!definition) return { error: { code: -32602, message: 'Herramienta desconocida.' } }
    const args = params.arguments === undefined ? {} : params.arguments
    const invalid = validate(args, definition)
    if (invalid) return { error: { code: -32602, message: invalid } }
    const data = definition.call(args)
    if (data === null) return { result: { isError: true, content: [{ type: 'text', text: 'Ficha no encontrada: ' + args.id }] } }
    const content = [{ type: 'text', text: JSON.stringify(data) }]
    return { result: version >= '2025-06-18' ? { content, structuredContent: data } : { content } }
  }
  return { error: { code: -32601, message: 'Método desconocido.' } }
}

input.on('line', line => {
  if (!line.trim()) return
  let request
  try {
    request = JSON.parse(line)
  } catch {
    write(null, { error: { code: -32700, message: 'JSON inválido.' } })
    return
  }

  if (request?.jsonrpc !== '2.0' || typeof request.method !== 'string') {
    write(null, { error: { code: -32600, message: 'Petición inválida.' } })
    return
  }

  if (!Object.hasOwn(request, 'id')) {
    if (request.method === 'notifications/initialized') initialized = true
    return
  }

  try {
    write(request.id, run(request))
  } catch (error) {
    console.error(error)
    write(request.id, { error: { code: -32603, message: 'Error interno al consultar la biblioteca.' } })
  }
})
