"""Capture the public Construct Design page for the GitHub Pages replica."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import urlopen


ORIGIN = "https://www.tobiadonadon.com"
CATALOGUE = "/projects/construct/design"
PAGES = {
    "index.html": "?kind=component",
    "mcp/index.html": "/mcp",
    "pricing/index.html": "/pricing",
}
STATIC = "/_next/static/"
IMAGES = re.compile(r"/design/(?:apps|components|site|websites)/[\w./-]+\.webp")
FONT = re.compile(r"\.\./media/([\w.-]+\.woff2(?:\?[^)'\"]+)?)")
ANALYTICS = re.compile(r'("analytics":\{"scriptSrc":")[\w/-]+/script\.js(")')
PATHNAME_HOOK = re.compile(
    r'("usePathname\(\)"\),)(\(0,[\w$]+\.useContext\)\([\w$]+\.PathnameContext\))'
)
AUTH_FIELD = re.compile(
    r'((?:type:"email",inputMode:"email"|type:[\w$]+\?"text":"password"),)'
    r'autoComplete:("(?:email|username)"|[\w$]+),'
)


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


def adapt_client(source, prefix):
    paths = {prefix + route + "/": CATALOGUE + route for route in PAGES.values() if route.startswith("/")}
    paths[prefix + "/"] = CATALOGUE
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
    # Keep the original dialogs and let the original domain accept credentials.
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


def download_asset(output, path):
    try:
        save_clientfile(output, path, fetch(path))
    except HTTPError as error:
        if error.code == 404 and path.startswith("/design/"):
            print(f"Imagen no disponible en el original: {path}", flush=True)
            return False
        raise
    return True


def capture(output, prefix):
    files = ClientFiles()
    images = set()
    fonts = set()
    browser = Path(__file__).with_name("construct-browser.js").read_text()
    browser = browser.replace("'__CONSTRUCT_MIRROR__'", json.dumps(prefix + "/"))
    with ThreadPoolExecutor(max_workers=5) as pool:
        for page, data in zip(PAGES, pool.map(fetch, (CATALOGUE + route for route in PAGES.values()))):
            html = data.decode()
            if "__next_f" not in html:
                raise ValueError(f"La página ya no entrega el HTML esperado: {page}")
            files.feed(html)
            images.update(IMAGES.findall(html))
            save_clientfile(output, "/" + page, static_copy(html, prefix).encode())
        if not files.urls:
            raise ValueError("La página ya no entrega los archivos de cliente esperados")
        paths = sorted(files.urls)
        for path, data in zip(paths, pool.map(fetch, paths)):
            source = data.decode()
            images.update(IMAGES.findall(source))
            fonts.update("/_next/static/media/" + name for name in FONT.findall(source))
            source = static_copy(source, prefix)
            source = ANALYTICS.sub(
                lambda match: match[1] + prefix.lstrip("/") + "/analytics-disabled.js" + match[2],
                source,
            )
            if urlsplit(path).path.endswith(".js"):
                source = adapt_client(source, prefix)
            if urlsplit(path).path.rsplit("/", 1)[-1].startswith("turbopack-"):
                source = browser + ";\n" + source
            save_clientfile(output, path, source.encode())

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
