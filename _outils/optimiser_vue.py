"""Trouve l'orientation initiale (yaw/pitch) la plus proche de la capture originale."""
import os
from PIL import Image
from playwright.sync_api import sync_playwright

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER = os.path.join(ICI, "verification")
REF = os.path.join(ICI, "capture-original", "screenshot-1440.png")
URL = "file:///D:/IA/ReconstitutionPaleoTerre/index.html#460"

original = Image.open(REF).convert("RGB")
# Zone du globe dans la capture originale 1440x904
ref = original.crop((475, 200, 960, 690)).resize((192, 192), Image.LANCZOS)
ref_px = list(ref.getdata())


def note(im):
    """Écart moyen absolu par canal, sur les seuls pixels du disque."""
    im = im.resize((192, 192), Image.LANCZOS)
    px = list(im.getdata())
    s = n = 0
    for i, (r, g, b) in enumerate(px):
        x = i % 192 - 96
        y = i // 192 - 96
        if x * x + y * y > 94 * 94:
            continue
        a = ref_px[i]
        s += abs(r - a[0]) + abs(g - a[1]) + abs(b - a[2])
        n += 3
    return round(s / n, 2)


candidats = [(-0.8, 0.06), (-0.6, 0.06), (-0.45, 0.06), (-0.3, 0.06),
             (-0.15, 0.06), (0.0, 0.06), (0.15, 0.06), (0.3, 0.06),
             (-0.45, 0.0), (-0.45, 0.12), (-0.3, 0.0), (-0.6, 0.0)]

scores = []
with sync_playwright() as p:
    nav = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
    ctx = nav.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page = ctx.new_page()
    page.goto(URL, wait_until="load", timeout=120000)
    page.wait_for_function("document.querySelector('#chargement').hidden===true", timeout=60000)
    page.evaluate("options.rotation=false")
    page.wait_for_timeout(300)
    tmp = os.path.join(DOSSIER, "opt-tmp.png")
    for yaw_v, pitch_v in candidats:
        page.evaluate("v => {yaw=v[0];pitch=v[1]}", [yaw_v, pitch_v])
        page.wait_for_timeout(120)
        page.screenshot(path=tmp)
        im = Image.open(tmp).convert("RGB").crop((477, 207, 963, 693))
        scores.append((note(im), yaw_v, pitch_v))
    ctx.close()
    nav.close()

scores.sort()
for s, y, pi in scores:
    print("écart", s, "| yaw", round(y, 3), "rad (", round(y * 180 / 3.14159, 1), "°) | pitch", pi)
print("MEILLEUR :", scores[0])
