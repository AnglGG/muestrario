const fs = require('node:fs')
const path = require('node:path')
const catalog = require('./catalog.json')
const recipeIndex = require('./recipes/index.json')

const read = name => fs.readFileSync(path.join(__dirname, name), 'utf8')
const recipes = recipeIndex.map(recipe => ({ ...recipe, code: read('recipes/' + recipe.id + '.html') }))
const snapshot = { ...catalog, recipes }
const data = JSON.stringify(snapshot).replace(/</g, '\\u003c')
const app = [read('src/library.js'), read('src/gallery.js')].join('\n').replace(/<\/script/gi, '<\\/script')

const replacements = {
  '__STYLES__': () => read('src/gallery.css'),
  '__SNAPSHOT__': () => data,
  '__APP__': () => app
}
const html = read('src/gallery.html').replace(/__(?:STYLES|SNAPSHOT|APP)__/g, key => replacements[key]())
fs.writeFileSync(path.join(__dirname, 'index.html'), html)
