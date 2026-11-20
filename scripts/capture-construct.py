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
STATIC = "/_next/static/"
IMAGES = re.compile(r"/design/(?:apps|components|site|websites)/[\w./-]+\.webp")
FONT = re.compile(r"\.\./media/([\w.-]+\.woff2(?:\?[^)'\"]+)?)")
ANALYTICS = re.compile(r'("analytics":\{"scriptSrc":")[\w/-]+/script\.js(")')


class ClientFiles(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = set()

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        asset = attributes.get("src" if tag == "script" else "href") or ""
        if tag in ("link", "script") and asset.startswith(STATIC):
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
    page_url = CATALOGUE + "?kind=component"
    html = fetch(page_url).decode()
    files = ClientFiles()
    files.feed(html)
    if "__next_f" not in html or not files.urls:
        raise ValueError("La página ya no entrega el HTML y los archivos esperados")
    images = set(IMAGES.findall(html))
    fonts = set()
    browser = Path(__file__).with_name("construct-browser.js").read_text()
    with ThreadPoolExecutor(max_workers=5) as pool:
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
    save_clientfile(output, "/index.html", static_copy(html, prefix).encode())
    print(f"{len(files.urls)} archivos de cliente y {downloaded}/{len(media)} recursos.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--prefix", default="/muestrario/construct")
    args = parser.parse_args()
    capture(args.output, args.prefix.rstrip("/"))
