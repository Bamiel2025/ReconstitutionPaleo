"""Calibre l'opacité des nuages par comparaison avec la capture originale."""
import os
from PIL import Image
from playwright.sync_api import sync_playwright

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER = os.path.join(ICI, "verification")
REF = os.path.join(ICI, "capture-original", "screenshot-1440.png")
URL = "file:///D:/IA/ReconstitutionPaleoTerre/index.html#460"

ref = Image.open(REF).convert("RGB").crop((475, 200, 960, 690)).resize((160, 160), Image.LANCZOS)
ref_px = list(ref.getdata())
disque = [(i % 160 - 80) ** 2 + (i // 160 - 80) ** 2 <= 78 ** 2 for i in range(160 * 160)]


def note(im):
    px = list(im.resize((160, 160), Image.LANCZOS).getdata())
    s = n = 0
    for i, (r, g, b) in enumerate(px):
        if not disque[i]:
            continue
        a = ref_px[i]
        s += abs(r - a[0]) + abs(g - a[1]) + abs(b - a[2])
        n += 3
    return round(s / n, 2)


valeurs = [0.0, 0.45, 0.62, 0.8, 1.0, 1.2, 1.5]
scores = []
with sync_playwright() as p:
    nav = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
    ctx = nav.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page = ctx.new_page()
    page.goto(URL, wait_until="load", timeout=120000)
    page.wait_for_function("document.querySelector('#chargement').hidden===true", timeout=60000)
    page.evaluate("options.rotation=false")
    tmp = os.path.join(DOSSIER, "nuages-tmp.png")
    for v in valeurs:
        page.evaluate("v => {forceNuages=v}", v)
        page.wait_for_timeout(140)
        page.screenshot(path=tmp)
        im = Image.open(tmp).convert("RGB").crop((477, 207, 963, 693))
        scores.append((note(im), v))
    ctx.close()
    nav.close()

for s, v in sorted(scores):
    print("écart", s, "| forceNuages", v)
print("MEILLEUR :", min(scores))
