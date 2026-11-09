"""Télécharge et compacte les frontières réellement reconstruites pour chaque date.

Format source (bundle original) : lignes delta-encodées en 1/scale degrés ;
les labels sont [nom, ?, lat*scale, lng*scale].
"""
import json, math, os, re, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ICI = os.path.dirname(os.path.abspath(__file__))
BRUT = os.path.join(ICI, "borders_brut")
os.makedirs(BRUT, exist_ok=True)
donnees = open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read()
STEPS = json.loads(re.search(r"const STEPS=(.*?);\n", donnees, re.S).group(1))
URL = "https://dinosaurpictures.org/ancient-earth-assets/borders/{}.json"


def telecharger(a):
    chemin = os.path.join(BRUT, str(a) + ".json")
    if os.path.exists(chemin) and os.path.getsize(chemin) > 1000:
        return a, True
    for essai in range(4):
        try:
            req = urllib.request.Request(URL.format(a), headers={"User-Agent": "Mozilla/5.0 (offline-edu)"})
            with urllib.request.urlopen(req, timeout=40) as r:
                octets = r.read()
            with open(chemin, "wb") as f:
                f.write(octets)
            return a, True
        except Exception as e:
            if essai == 3:
                return a, str(e)
            time.sleep(1 + essai)


with ThreadPoolExecutor(max_workers=5) as ex:
    res = list(ex.map(telecharger, STEPS))
problemes = [(a, r) for a, r in res if r is not True]
print("Téléchargés :", len(res) - len(problemes), "/", len(res), "| problèmes :", problemes[:8], flush=True)


def rdp(pts, tol):
    if len(pts) < 3:
        return pts
    ax, ay = pts[0]
    bx, by = pts[-1]
    dx, dy = bx - ax, by - ay
    n = math.hypot(dx, dy)
    imax, dmax = 0, -1
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        if n < 1e-9:
            d = math.hypot(px - ax, py - ay)
        else:
            d = abs(dy * px - dx * py + bx * ay - by * ax) / n
        if d > dmax:
            imax, dmax = i, d
    if dmax > tol:
        return rdp(pts[:imax + 1], tol)[:-1] + rdp(pts[imax:], tol)
    return [pts[0], pts[-1]]


TOL = 0.55          # degrés
Q = 10              # précision 0,1°
sortie = {}
noms = set()
points_avant = points_apres = 0

for a in STEPS:
    chemin = os.path.join(BRUT, str(a) + ".json")
    if not os.path.exists(chemin):
        continue
    d = json.load(open(chemin, encoding="utf-8"))
    s = d["scale"]
    lignes = []
    for line in d["lines"]:
        lat = lng = 0
        pts = []
        for i in range(0, len(line), 2):
            lat += line[i]
            lng += line[i + 1]
            pts.append((lat / s, lng / s))
        points_avant += len(pts)
        if len(pts) < 2:
            continue
        simp = rdp(pts, TOL)
        if len(simp) < 2:
            simp = [pts[0], pts[-1]]
        # quantification + delta
        q = [(round(p[0] * Q), round(p[1] * Q)) for p in simp]
        preceding = None
        net = []
        for p in q:
            if preceding is None:
                net = [p[0], p[1]]
                preceding = p
            elif p != preceding:
                net.extend([p[0] - preceding[0], p[1] - preceding[1]])
                preceding = p
        if len(net) >= 4:
            lignes.append(net)
            points_apres += len(net) // 2
    etiquettes = []
    for l in d.get("labels", []):
        noms.add(l[0])
        etiquettes.append([l[0], round(l[2] / s * Q), round(l[3] / s * Q)])
    sortie[str(a)] = {"l": lignes, "n": etiquettes}

chemin_js = os.path.join(ICI, "borders_genere.js")
with open(chemin_js, "w", encoding="utf-8") as f:
    f.write("const FRONTIERES_PALEO=" + json.dumps(sortie, separators=(",", ":")) + ";\n")
    f.write("const NOMS_PAYS=" + json.dumps(sorted(noms), ensure_ascii=False, separators=(",", ":")) + ";\n")

print("Points avant/après :", points_avant, "->", points_apres, flush=True)
print("Années :", len(sortie), "| noms de pays distincts :", len(noms), flush=True)
print("Taille JS :", os.path.getsize(chemin_js), "octets", flush=True)
print("Noms :", sorted(noms)[:25], flush=True)
