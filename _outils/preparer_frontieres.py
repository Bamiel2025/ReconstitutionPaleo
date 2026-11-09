# -*- coding: utf-8 -*-
"""Extrait un repère de frontières modernes compact (Natural Earth 1:110m, domaine public)."""
import json, os, sys

sys.setrecursionlimit(20000)
ROOT = r"D:/IA/ReconstitutionPaleoTerre/_outils"
geo = json.load(open(os.path.join(ROOT, "brut/pays.geojson"), encoding="utf-8"))


def rdp(pts, eps):
    if len(pts) < 3:
        return pts
    ax, ay = pts[0]
    bx, by = pts[-1]
    dx, dy = bx - ax, by - ay
    n = (dx * dx + dy * dy) ** 0.5
    if n < 1e-9:
        # Segment dégénéré : garder les extrémités et le point médian.
        return [pts[0], pts[len(pts) // 2], pts[-1]]
    dmax, idx = -1, 0
    for i in range(1, len(pts) - 1):
        px, py = pts[i]
        d = abs(dy * px - dx * py + bx * ay - by * ax) / n
        if d > dmax:
            dmax, idx = d, i
    if dmax > eps and idx > 0 and idx < len(pts) - 1:
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
        if ring and ring[0] == ring[-1]:
            ring = ring[:-1]
        if len(ring) < 4:
            continue
        pts = [[round(p[0], 2), round(p[1], 2)] for p in ring]
        simp = rdp(pts, 0.5)
        if len(simp) < 3:
            simp = pts[:: max(1, len(pts) // 12)]
        if len(simp) >= 3:
            anneaux.append(simp)
    if not anneaux:
        continue
    # Étiquette au centre du plus grand anneau
    grand = max(anneaux, key=len)
    xs = [p[0] for p in grand]
    ys = [p[1] for p in grand]
    pays.append({"n": nom, "c": [round(sum(xs) / len(xs), 2), round(sum(ys) / len(ys), 2)],
                 "a": round((max(xs) - min(xs)) * (max(ys) - min(ys)), 1), "p": anneaux})

pays.sort(key=lambda p: -p["a"])
with open(os.path.join(ROOT, "frontieres.json"), "w", encoding="utf-8") as f:
    json.dump(pays, f, ensure_ascii=False, separators=(",", ":"))

# Remplace la ligne FRONTIERES du fragment généré
p = os.path.join(ROOT, "cartes_generees.js")
lignes = [l for l in open(p, encoding="utf-8").read().splitlines() if not l.startswith("const FRONTIERES=")]
lignes.append("const FRONTIERES=" + json.dumps(pays, ensure_ascii=False, separators=(",", ":")) + ";")
open(p, "w", encoding="utf-8").write("\n".join(lignes) + "\n")
print(len(pays), "pays,", sum(len(a) for p in pays for a in p["p"]), "points,",
      os.path.getsize(os.path.join(ROOT, "frontieres.json")) // 1024, "Ko")
print("Exemples :", [p["n"] for p in pays[:12]])
