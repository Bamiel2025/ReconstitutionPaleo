"""Compare plusieurs orientations initiales du globe à la capture originale."""
import os
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verification")
URL = "file:///D:/IA/ReconstitutionPaleoTerre/index.html#460"
YAWS = [("0 deg (lon 0)", 0.0), ("90 deg", 1.5708), ("180 deg", 3.1416),
        ("240 deg (actuel)", 4.18879), ("270 deg", 4.71239), ("300 deg", 5.23599)]

cases = []
with sync_playwright() as p:
    nav = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
    ctx = nav.new_context(viewport={"width": 1000, "height": 700}, device_scale_factor=1)
    page = ctx.new_page()
    page.goto(URL, wait_until="load", timeout=120000)
    page.wait_for_function("document.querySelector('#chargement').hidden===true", timeout=60000)
    page.evaluate("options.rotation=false")
    for nom, valeur in YAWS:
        page.evaluate("y => {yaw=y}", valeur)
        page.wait_for_timeout(160)
        chemin = os.path.join(DOSSIER, "yaw-tmp.png")
        page.screenshot(path=chemin, clip={"x": 280, "y": 100, "width": 440, "height": 440})
        cases.append((nom, Image.open(chemin).convert("RGB").copy()))
    ctx.close()
    nav.close()

# Ajoute la référence originale recadrée sur le globe
original = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture-original", "screenshot-1440.png")).convert("RGB")
o = original.resize((1000, round(1000 * original.height / original.width)))
# recadrage approximatif du globe dans la capture originale (1200x772 affichée)
ref = Image.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "capture-original", "screenshot-1440.png")).convert("RGB")
w, h = ref.size
cw = int(w * 0.34)
ref = ref.crop((int(w * 0.32), int(h * 0.22), int(w * 0.32) + cw, int(h * 0.22) + cw)).resize((440, 440))
cases.insert(0, ("ORIGINAL 460 Ma", ref))

largeur_case, hauteur_case = 440, 470
colonnes = 4
lignes = (len(cases) + colonnes - 1) // colonnes
planche = Image.new("RGB", (colonnes * largeur_case, lignes * hauteur_case), (18, 18, 18))
d = ImageDraw.Draw(planche)
for i, (nom, im) in enumerate(cases):
    x = (i % colonnes) * largeur_case
    y = (i // colonnes) * hauteur_case
    planche.paste(im, (x, y + 30))
    d.text((x + 8, y + 8), nom, fill=(255, 235, 90))
out = os.path.join(DOSSIER, "planche-orientations.png")
planche.save(out)
print("Planche :", out, "| taille originale :", w, h)
