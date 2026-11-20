# Muestrario

Biblioteca de interfaz. Reúne 184 referencias públicas de Construct de Tobia Donadon, con 120 componentes, 33 apps y 31 webs. Incluye ocho patrones originales con HTML, CSS y JavaScript editables.

## Réplica de Construct

La réplica de la galería pública usa el HTML, los estilos, los archivos JavaScript de cliente y los recursos que publica Construct. El código y el diseño de la réplica son de [Tobia Donadon](https://www.tobiadonadon.com/projects/construct/design?kind=component).

- **En GitHub Pages**, cuando esté activo, abre la [réplica](https://anglgg.github.io/muestrario/construct/?kind=component).
- **En tu equipo**, clona el repositorio en una carpeta llamada `muestrario`. Desde la carpeta que la contiene, ejecuta `python3 -m http.server 8000 --bind 127.0.0.1` y abre `http://127.0.0.1:8000/muestrario/construct/?kind=component`.

La réplica incluye la galería, la búsqueda y las demos navegables. Puedes explorar las vistas previas sin registro. La pestaña [MCP](https://anglgg.github.io/muestrario/construct/mcp/) explica cómo conectar el catálogo y los patrones originales a tu IA.

Para actualizar la captura, ejecuta `python3 scripts/capture-construct.py <carpeta-temporal>`. La ruta pública predeterminada es `/muestrario/construct/`. Si el conjunto de fichas cambia, actualiza `catalog.json` antes de regenerar la captura.

## Galería

Abre la [galería en GitHub Pages](https://anglgg.github.io/muestrario/) o descarga el repositorio y abre `index.html` en el navegador. Filtra por tipo o categoría y busca términos como «arrastre», «vidrio» o «confirmación». En **Patrones originales** puedes interactuar con cada ejemplo y copiar su código. La búsqueda, las fichas y las demos originales funcionan sin conexión. Las miniaturas de apps y webs y los enlaces a Construct usan Internet.

## MCP local

Descarga el repositorio o clónalo con `git clone https://github.com/AnglGG/muestrario.git`. Necesitas Node.js 22 o posterior. El cliente de IA ejecuta el servidor en tu equipo por **stdio**, sin puerto, cuenta, clave ni dependencias adicionales.

- **Claude Desktop, Cursor y clientes con `mcpServers`**. Añade la entrada `muestrario` de [mcp-config.example.json](mcp-config.example.json) a la configuración del cliente y sustituye la ruta de ejemplo por la ruta absoluta a `mcp.cjs`. Si tu cliente no encuentra `node`, indica la ruta absoluta al ejecutable de Node.js.
- **Claude Code**. Ejecuta este comando desde la carpeta del repositorio en macOS o Linux.

  ```sh
  claude mcp add --transport stdio --scope user muestrario -- "$(command -v node)" "$PWD/mcp.cjs"
  ```

- **Codex CLI**. Ejecuta este comando desde la carpeta del repositorio en macOS o Linux.

  ```sh
  codex mcp add muestrario -- "$(command -v node)" "$PWD/mcp.cjs"
  ```

### Herramientas

- `search_library` busca por nombre, interacción, tipo, categoría, descripción y controles. Admite paginación. Usa `type: "recipe"` si necesitas código.
- `get_entry` abre una ficha por su ID. Devuelve código completo para los patrones originales. Para las referencias, devuelve la descripción, los nombres de los controles, la vista previa en Muestrario, la fuente y la miniatura donde esté disponible.
- `list_categories` da los identificadores de las categorías y cuántas fichas tienen.

El recurso `muestrario://catalogue` entrega el índice completo en JSON con la procedencia, las 184 referencias y los ocho patrones. También puedes recorrer el catálogo con `search_library` mediante `nextOffset`.

Prueba este encargo con tu IA.

> Utiliza Muestrario para buscar un patrón de confirmación para archivar notas. Abre el ejemplo con código, compáralo con dos referencias y adáptalo al diseño y a los componentes de este proyecto.

## Añadir patrones

El índice de referencias está en `catalog.json` y las descripciones y controles públicos capturados están en `construct/details.json`. Cada patrón se describe en `recipes/index.json` y tiene un archivo HTML del mismo nombre en `recipes/`. Para regenerar la galería después de editar, ejecuta `node build.cjs` en esta carpeta. El MCP lee esos archivos al arrancar.

Fuente del catálogo y sus miniaturas. [Construct, Tobia Donadon](https://www.tobiadonadon.com/projects/construct/design)

## Licencia

El código propio de Muestrario y los ocho patrones originales se publican con [licencia MIT](LICENSE). El código, el diseño y los recursos de Construct conservan los términos de sus respectivos titulares. Puedes explorar Muestrario y conectar el MCP sin cuenta ni cuota.
