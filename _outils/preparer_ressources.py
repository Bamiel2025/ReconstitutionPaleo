"""Télécharge les cartes paléogéographiques (CC BY 4.0), les optimise et les encode
pour une intégration hors ligne dans un unique fichier HTML.

Sources :
  - images : https://dinosaurpictures.org/ancient-earth-assets/images/paleo/<mya>.jpg
    rendues à partir des modèles numériques de terrain paléo de C.R. Scotese & Wright (2018),
    PALEOMAP Paleodigital Elevation Models for the Phanerozoic, CC BY 4.0 ;
    côtes : Kocsis & Scotese (2021), CC BY 4.0 ; > 540 Ma : Merdith et al. (2021), GPlates.
  - frontières modernes : Natural Earth 1:110m (domaine public).
"""
import base64, io, json, os, re, sys, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

ROOT = r"D:/IA/ReconstitutionPaleoTerre"
OUT = os.path.join(ROOT, "_outils")
BRUT = os.path.join(OUT, "brut")
WEBP = os.path.join(ROOT, "cartes")
os.makedirs(BRUT, exist_ok=True)
os.makedirs(WEBP, exist_ok=True)

BASE = "https://dinosaurpictures.org/ancient-earth-assets/images/paleo/"
UA = {"User-Agent": "Mozilla/5.0 (compatible; PaleoTerre-education/1.0)"}

page = open(os.path.join(OUT, "page_originale.html"), encoding="utf-8", errors="replace").read()
options = [int(v) for v in re.findall(r'<option value="(\d+)"', page)]
donnees = json.load(open(os.path.join(OUT, "periodes_en.json"), encoding="utf-8"))
cles = sorted((d["mya"] for d in donnees), reverse=True)
steps = options[: len(cles)]
assert steps == cles, "Les pas de la frise ne correspondent pas au jeu de données"
print("Pas de temps :", len(steps), "de", steps[0], "à", steps[-1], "Ma", flush=True)


def telecharger(url, chemin):
    if os.path.exists(chemin) and os.path.getsize(chemin) > 1000:
        return chemin
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r, open(chemin, "wb") as f:
        f.write(r.read())
    return chemin


def convertir(mya):
    src = os.path.join(BRUT, f"{mya}.jpg")
    telecharger(f"{BASE}{mya}.jpg", src)
    im = Image.open(src).convert("RGB")
    im = im.resize((1600, 800), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=65, method=6)
    data = buf.getvalue()
    # Version dossier (consultable, et réutilisable par d'autres projets)
    with open(os.path.join(WEBP, f"{mya}.webp"), "wb") as f:
        f.write(data)
    return mya, "data:image/webp;base64," + base64.b64encode(data).decode("ascii")


resultats = {}
with ThreadPoolExecutor(max_workers=10) as pool:
    fut = {pool.submit(convertir, y): y for y in steps}
    for i, f in enumerate(as_completed(fut), 1):
        y, b64 = f.result()
        resultats[y] = b64
        if i % 20 == 0:
            print(f"  {i}/{len(steps)} cartes", flush=True)

# Nuages
chem_nuages = os.path.join(BRUT, "nuages.png")
telecharger("https://dinosaurpictures.org/ancient-earth-assets/images/fair_clouds_4k.png", chem_nuages)
im = Image.open(chem_nuages).convert("RGBA")
im = im.resize((1600, 800), Image.LANCZOS)
buf = io.BytesIO()
im.save(buf, "WEBP", quality=62, method=6)
nuages = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
with open(os.path.join(WEBP, "nuages.webp"), "wb") as f:
    f.write(buf.getvalue())

# Frontières modernes (Natural Earth 1:110m, domaine public)
geo_url = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
geo_path = os.path.join(BRUT, "pays.geojson")
telecharger(geo_url, geo_path)
geo = json.load(open(geo_path, encoding="utf-8"))


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    ax, ay = pts[0]
    bx, by = pts[-1]
    dx, dy = bx - ax, by - ay
    n = (dx * dx + dy * dy) ** 0.5 or 1e-9
    dmax, idx = -1, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs(dy * px - dx * py + bx * ay - by * ax) / n
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps:
        return rdp(pts[: idx + 1], eps)[:-1] + rdp(pts[idx:], eps)
    return [pts[0], pts[-1]]


pays = []
for feat in geo["features"]:
    g = feat.get("geometry") or {}
    if g.get("type") not in ("Polygon", "MultiPolygon"):
        continue
    props = feat.get("properties") or {}
    nom = props.get("NAME_FR") or props.get("NAME") or ""
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    anneaux = []
    for poly in polys:
        ring = poly[0]
        if len(ring) < 4:
            continue
        simp = rdp([[round(p[0], 2), round(p[1], 2)] for p in ring], 0.55)
        if len(simp) >= 3:
            anneaux.append(simp)
    if not anneaux:
        continue
    xs = [p[0] for a in anneaux for p in a]
    ys = [p[1] for a in anneaux for p in a]
    pays.append({"n": nom, "c": [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)], "p": anneaux})

with open(os.path.join(OUT, "frontieres.json"), "w", encoding="utf-8") as f:
    json.dump(pays, f, ensure_ascii=False, separators=(",", ":"))

# Fragments JS injectés dans le modèle
with open(os.path.join(OUT, "cartes_generees.js"), "w", encoding="utf-8") as f:
    f.write("const CARTES=" + json.dumps(resultats, separators=(",", ":")) + ";\n")
    f.write("const NUAGES=" + json.dumps(nuages) + ";\n")
    f.write("const FRONTIERES=" + json.dumps(pays, ensure_ascii=False, separators=(",", ":")) + ";\n")

taille = os.path.getsize(os.path.join(OUT, "cartes_generees.js"))
print("Terminé :", len(resultats), "cartes,", len(pays), "pays, fragment JS de", taille // 1024, "Ko", flush=True)
