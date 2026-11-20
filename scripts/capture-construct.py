"""Capture the public Construct Design page for the GitHub Pages replica."""

import argparse
from ast import literal_eval
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen


ORIGIN = "https://www.tobiadonadon.com"
CATALOGUE = "/projects/construct/design"
REPO_ROOT = Path(__file__).resolve().parents[1]
STATIC = "/_next/static/"
CLIENT_URL_SUFFIX = re.compile(r"\.(?:css|js)\?dpl=[\w-]+")
IMAGES = re.compile(r"/design/(?:apps|components|site|websites)/[\w./-]+\.webp")
FONT = re.compile(r"\.\./media/([\w.-]+\.woff2(?:\?[^)'\"]+)?)")
ANALYTICS = re.compile(r'("analytics":\{"scriptSrc":")[\w/-]+/script\.js(")')
JS_STRING = r"""(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')"""
PUBLIC_DETAILS = re.compile(
    rf'\{{slug:({JS_STRING}),kind:"(?:component|app|website)",component:{JS_STRING},'
    rf'title:{JS_STRING},category:{JS_STRING},description:({JS_STRING}),'
    r'(?:(?!\{slug:).)*?controls:(.*?),howItWorks:',
    re.DOTALL,
)
CONTROL_LABEL = re.compile(rf'\{{prop:{JS_STRING},label:({JS_STRING}),type:')
PATHNAME_HOOK = re.compile(
    r'("usePathname\(\)"\),)(\(0,[\w$]+\.useContext\)\([\w$]+\.PathnameContext\))'
)
AUTH_FIELD = re.compile(
    r'((?:type:"email",inputMode:"email"|type:[\w$]+\?"text":"password"),)'
    r'autoComplete:("(?:email|username)"|[\w$]+),'
)
CATALOGUE_PROMOTIONS = re.compile(
    r'<div class="mx-auto max-w-\[46rem\] py-16"><section aria-labelledby="cd-steps">.*?</section></div>'
    r'<section aria-labelledby="cd-answers"[^>]*>.*?</section>(?=</main>)',
    re.DOTALL,
)
HERO_DESCRIPTION = "Explore interactive components, websites and app screens. Connect Muestrario to search references and reuse original patterns in your projects."
FOOTER_DESCRIPTION = "Interactive components, websites and app screens."


class ClientFiles(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        asset = attributes.get("src" if tag == "script" else "href") or ""
        if tag in ("link", "script") and asset.startswith(STATIC + "chunks/"):
            self.urls.add(asset)


def fetch(path):
    with urlopen(ORIGIN + path, timeout=30) as response:
        if urlsplit(response.url).netloc != urlsplit(ORIGIN).netloc:
            raise ValueError(f"El recurso cambió de origen: {path}")
        return response.read()


def static_copy(source, prefix):
    source = source.replace("/_next/", prefix + "/_next/")
    source = source.replace(prefix + "/_next/image", ORIGIN + "/_next/image")
    return IMAGES.sub(lambda match: prefix + match[0], source)


def replace_fragment(source, fragment, replacement):
    if source.count(fragment) != 1:
        raise ValueError(f"El frontend cambió junto a {fragment[:100]}")
    return source.replace(fragment, replacement, 1)


def replace_pattern(source, pattern, replacement):
    source, matches = re.subn(pattern, lambda _: replacement, source, flags=re.DOTALL)
    if matches != 1:
        raise ValueError(f"El frontend cambió junto a {pattern[:100]}")
    return source


def apply_catalogue_copy(source):
    return source.replace(
        'Hand-made components, website heroes and app screens. Connect once, and Claude, Cursor or Codex drops the real thing into your project.',
        HERO_DESCRIPTION,
        1,
    ).replace(
        'Hand-made components, websites and app screens, live and ready for your AI to build with.',
        FOOTER_DESCRIPTION,
        1,
    )


def clean_catalogue_html(html):
    html = replace_pattern(
        html,
        r'<button type="button" class="cd-cta-ink inline-flex h-12 [^"]+">Join for free<svg.*?</svg></button>',
        '<a href="#library" class="cd-cta-ink inline-flex h-12 items-center gap-2 rounded-full px-6 text-[15px]">'
        'Open the library</a>',
    )
    for element in (
        '<span class="h-11 w-[13rem] max-sm:w-[6rem]" aria-hidden="true"></span>',
        '<a class="hover:text-[#17181a]" href="/projects/construct/design/pricing">Pricing</a>',
        '<a class="hover:text-[#17181a]" href="/projects/construct/account?from=design">Account</a>',
        '<p class="mt-7 h-5" aria-hidden="true"></p>',
    ):
        html = replace_fragment(html, element, '')
    return apply_catalogue_copy(replace_fragment(html, '>Free designs<', '>Featured designs<'))


def adapt_catalogue_html(html):
    # Keep the initial document consistent with DesignHome during hydration.
    html, sections = CATALOGUE_PROMOTIONS.subn('', html)
    if sections != 1:
        raise ValueError("Cambió el final de la galería de Construct")
    html = replace_fragment(html, '<main class="px-4 md:px-5">', '<main class="px-4 pb-10 md:px-5">')
    return clean_catalogue_html(html)


def clean_catalogue_client(source):
    source = replace_pattern(
        source,
        r',"loading"===e\?\(0,t\.jsx\)\("span",\{className:"h-11 w-\[13rem\].*?\(0,t\.jsx\)\(tB,\{access:e\}\)\]\}\)',
        '',
    )
    source = replace_pattern(
        source,
        r'"member"===e\?\(0,t\.jsxs\)\("a",\{href:"#library".*?(?=,\(0,t\.jsxs\)\(y\.default,\{href:\x60\$\{tk\}/mcp\x60)',
        '(0,t.jsx)("a",{href:"#library",className:n,children:"Open the library"})',
    )
    source = replace_fragment(source, 'function tU(){let e=(0,J.useAccess)(),n=', 'function tU(){let n=')
    source = replace_fragment(source, 'children:"Free designs"', 'children:"Featured designs"')
    for element in (
        ',(0,t.jsx)(tK,{})',
        ',(0,t.jsx)(y.default,{href:`${tk}/pricing`,className:"hover:text-[#17181a]",children:"Pricing"})',
        ',(0,t.jsx)(y.default,{href:`${G.ACCOUNT_HREF}?from=design`,className:"hover:text-[#17181a]",children:"Account"})',
    ):
        source = replace_fragment(source, element, '')
    source = replace_fragment(source, 'function tH({open:e,onClose:s}){let a=(0,J.useAccess)(),', 'function tH({open:e,onClose:s}){let ')
    source = replace_pattern(
        source,
        r',"loading"===a\|\|\(0,J\.canSee\)\(a,e\)\?null:\(0,t\.jsx\)\("span",\{className:"[^"]+",children:"Pro"\}\)',
        '',
    )

    source = replace_pattern(
        source,
        r'function te\(\{block:e,allowed:n,source:s,onLoad:a,what:i="code"\}\)\{.*?(?=function tt\()',
        'function te({block:e,what:i="code"}){let n="prompt"===i;return(0,t.jsxs)("div",'
        '{className:"absolute inset-0 flex flex-col items-center justify-center gap-4 p-6 text-center",children:['
        '(0,t.jsx)("p",{className:"text-[1.02rem] font-medium",children:n?"Use this reference with your AI":"Editable patterns live in Muestrario"}),'
        '(0,t.jsx)("a",{href:n?"mcp/":"../#ficha/"+e.slug,className:"underline underline-offset-4",'
        'children:n?"Connect Muestrario":"View related patterns"})]})}',
    )
    source = replace_pattern(
        source,
        r'function tl\(\{block:e,access:s,allowed:a,source:i,onLoad:l,usage:r,tuned:o\}\)\{.*?(?=function to\()',
        'function tl({block:e}){return(0,t.jsx)("a",{href:"../#ficha/"+e.slug,className:ta,children:"Open in Muestrario"})}',
    )
    return apply_catalogue_copy(source)


def clean_catalogue_css(source):
    if ".site-footer" in source:
        return source + '\nfooter li:has(> a[href*="/projects/construct/join"]) { display: none; }\n'
    return source


def adapt_gallery(source):
    # Keep server-rendered cards through hydration. Add public previews once the
    # anonymous account request resolves, with the existing open cards first.
    replacements = (
        # Preserve the gallery's child position and width in React's ID tree.
        (
            '(0,t.jsxs)("main",{className:"px-4 md:px-5",children:[(0,t.jsx)(tf,{}),'
            '(0,t.jsx)("div",{className:"mx-auto max-w-[46rem] py-16",children:(0,t.jsx)(tG,{})}),'
            '(0,t.jsx)(tQ,{})]})',
            '(0,t.jsxs)("main",{className:"px-4 pb-10 md:px-5",children:[(0,t.jsx)(tf,{}),null,null]})',
        ),
        (
            ',(0,n.useEffect)(()=>{if("guest"!==e)return;let t="1";'
            'try{t=localStorage.getItem("cd:welcomed")??""}catch{}'
            'if(t||new URLSearchParams(window.location.search).has("block"))return;'
            'let n=setTimeout(()=>{q.current||(f(!0),V("join"),l(!0))},1400);'
            'return()=>clearTimeout(n)},[e,V])',
            '',
        ),
        (
            'u="member"===e,m="guest"===e||"free"===e,p=(0,n.useRef)(u);'
            '(0,n.useEffect)(()=>{p.current=u},[u]);',
            'u="loading"!==e;',
        ),
        (
            'let t=e?es.BLOCKS.find(t=>t.slug===e):null;'
            'if(t&&!p.current&&!(0,J.isOpen)(t))return void(0,J.openDoor)({step:"plan",slug:t.slug});',
            '',
        ),
        (
            '()=>u?f:f.filter(J.isOpen).sort((e,t)=>e.kind===t.kind?(0,J.openRank)(e)-(0,J.openRank)(t):0),'
            '[u,f]),b=(0,n.useMemo)(()=>u?[]:f.filter(e=>!(0,J.isOpen)(e)),[u,f])',
            '()=>(u?[...f]:f.filter(J.isOpen)).sort((e,t)=>e.kind===t.kind?(0,J.openRank)(e)-(0,J.openRank)(t):0),'
            '[u,f])',
        ),
        (
            'k=v&&(u||(0,J.isOpen)(v))?v:null;'
            '(0,n.useEffect)(()=>{if(!m||!v||(0,J.isOpen)(v))return;'
            'let e=requestAnimationFrame(()=>{o(null),(0,J.openDoor)({step:"plan",slug:v.slug})});'
            'return()=>cancelAnimationFrame(e)},[m,v]);',
            'k=v;',
        ),
        (
            'let s="component"===e.id;return(0,t.jsxs)("div",{children:[',
            'return(0,t.jsxs)("div",{children:[',
        ),
        (
            'm&&s?(0,t.jsx)(ty,{kind:e.id,blocks:b.filter(t=>t.kind===e.id),total:b.length,every:!0}):',
            '',
        ),
        (',m&&b.length?(0,t.jsx)(ty,{kind:s,blocks:b,total:b.length}):null', ''),
        ('(ef.sound.pop(),s(),l(""),(0,J.canSee)(a,e))?', 'ef.sound.pop(),s(),l("");'),
        (
            'new CustomEvent("cd:open",{detail:e.slug})):(0,J.openDoor)({step:"plan",slug:e.slug})};',
            'new CustomEvent("cd:open",{detail:e.slug}))};',
        ),
    )
    for fragment, replacement in replacements:
        source = replace_fragment(source, fragment, replacement)
    return source


def adapt_client(source, prefix):
    paths = {prefix + "/": CATALOGUE}
    # Keep Next's UI pathname canonical so the server-rendered navigation matches.
    source = PATHNAME_HOOK.sub(
        lambda match: f'{match[1]}(path=>({json.dumps(paths)})[path]??path)({match[2]})',
        source,
    )
    if not ("cd:kind" in source and "cd:open" in source):
        return source

    route = re.search(r'\blet ([\w$]+)="' + re.escape(CATALOGUE) + r'",', source)
    if not route:
        raise ValueError("No se pudo adaptar la navegación de Construct")
    binding = re.escape(route[1])
    source, checks = re.subn(
        r'(window\.location\.pathname(?:===|!==))' + binding + r'\b',
        lambda match: match[1] + json.dumps(prefix + "/"),
        source,
    )
    source, jumps = re.subn(
        r'(window\.location\.assign\(`)\$\{' + binding + r'\}(?=\?)',
        lambda match: match[1] + prefix + "/",
        source,
    )
    source = adapt_gallery(source)
    source = clean_catalogue_client(source)
    # Keep any credential fields inert in the static copy.
    source, fields = AUTH_FIELD.subn(
        lambda match: (
            match[1] + 'readOnly:!0,autoComplete:"off",title:"Continue on tobiadonadon.com",'
            + ('"data-account-mode":"signin",' if match[2] == '"username"' else "")
        ),
        source,
    )
    if (checks, jumps, fields) != (3, 2, 4):
        raise ValueError(
            f"El frontend cambió ({checks} comparaciones, {jumps} saltos, {fields} campos). "
            "Revisa la navegación y los diálogos antes de publicar."
        )
    return source.replace(
        'sub:"Type your email and we\'ll send you a code."',
        'sub:"Choose Forgot it? on Construct to reset your password."',
        1,
    ).replace('children:"Send the code"', 'children:"Open Construct sign-in"', 1)


def save_clientfile(output, path, content):
    parts = urlsplit(path).path.lstrip("/").split("/")
    if ".." in parts:
        raise ValueError(f"Ruta de recurso no válida: {path}")
    target = output.joinpath(*parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def client_revision(assets):
    checksum = sha256()
    for path, content in sorted(assets.items()):
        checksum.update(path.encode())
        checksum.update(b"\0")
        checksum.update(content)
    return checksum.hexdigest()[:12]


def version_client_urls(html, revision):
    # The streamed document may split a chunk path across two script tags.
    return CLIENT_URL_SUFFIX.sub(lambda match: f"{match[0]}&mirror={revision}", html)


def download_asset(output, path):
    try:
        save_clientfile(output, path, fetch(path))
    except HTTPError as error:
        if error.code == 404 and path.startswith("/design/"):
            print(f"Imagen no disponible en el original: {path}", flush=True)
            return False
        raise
    return True


def redirect_page(destination, label):
    return (
        '<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<meta http-equiv="refresh" content="0; url={destination}">\n'
        f'<title>{label} · Muestrario</title>\n<a href="{destination}">{label}</a>\n</html>\n'
    ).encode()


def decode_string(value):
    return literal_eval(value) if value.startswith("'") else json.loads(value)


def capture(output, prefix):
    catalog = json.loads((REPO_ROOT / "catalog.json").read_text())
    expected = {entry["id"] for entry in catalog["references"]}
    files = ClientFiles()
    assets = {}
    details = {}
    images = set()
    fonts = set()
    browser = Path(__file__).with_name("construct-browser.js").read_text()
    browser = browser.replace("'__CONSTRUCT_MIRROR__'", json.dumps(prefix + "/"))
    html = fetch(CATALOGUE + "?kind=component").decode()
    if "__next_f" not in html:
        raise ValueError("La galería ya no entrega el HTML esperado")
    files.feed(html)
    images.update(IMAGES.findall(html))
    html = static_copy(adapt_catalogue_html(html), prefix)
    with ThreadPoolExecutor(max_workers=5) as pool:
        if not files.urls:
            raise ValueError("La página ya no entrega los archivos de cliente esperados")
        paths = sorted(files.urls)
        for path, data in zip(paths, pool.map(fetch, paths)):
            source = data.decode()
            details.update({
                decode_string(slug): {
                    "description": decode_string(description),
                    "controls": [decode_string(label) for label in CONTROL_LABEL.findall(controls)],
                }
                for slug, description, controls in PUBLIC_DETAILS.findall(source)
            })
            images.update(IMAGES.findall(source))
            fonts.update("/_next/static/media/" + name for name in FONT.findall(source))
            source = static_copy(source, prefix)
            source = ANALYTICS.sub(
                lambda match: match[1] + prefix.lstrip("/") + "/analytics-disabled.js" + match[2],
                source,
            )
            filename = urlsplit(path).path.rsplit("/", 1)[-1]
            if filename.endswith(".js"):
                source = adapt_client(source, prefix)
            elif filename.endswith(".css"):
                source = clean_catalogue_css(source)
            if filename.startswith("turbopack-"):
                source = browser + ";\n" + source
            assets[path] = source.encode()

        missing = sorted(expected - details.keys())
        extra = sorted(details.keys() - expected)
        if missing or extra:
            raise ValueError(
                f"La captura no coincide con catalog.json. Faltan: {missing}. Sobran: {extra}. "
                "Comprueba el formato de las fichas y el índice antes de publicar."
            )
        revision = client_revision(assets)
        for path, content in assets.items():
            save_clientfile(output, path, content)
        save_clientfile(output, "/index.html", version_client_urls(html, revision).encode())
        save_clientfile(output, "/details.json", (json.dumps(details, ensure_ascii=False, indent=2) + "\n").encode())
        save_clientfile(output, "/mcp/index.html", (REPO_ROOT / "construct/mcp/index.html").read_bytes())
        save_clientfile(output, "/pricing/index.html", redirect_page("../", "Open the catalogue"))

        media = sorted(images | fonts)
        downloaded = sum(pool.map(lambda path: download_asset(output, path), media))

    account = json.loads(fetch("/api/account/me"))
    if account != {"ok": True, "member": None}:
        raise ValueError("La captura requiere una sesión anónima")
    save_clientfile(output, "/stats.json", fetch("/api/design/stats"))
    save_clientfile(output, "/analytics-disabled.js", b"// Analytics stays on the original site.\n")
    print(f"{len(files.urls)} archivos de cliente y {downloaded}/{len(media)} recursos.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prefix", default="/muestrario/construct")
    args = parser.parse_args()
    capture(args.output, args.prefix.rstrip("/"))
