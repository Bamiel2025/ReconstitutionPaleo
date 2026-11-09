"""Vérifie QUE les coordonnées (frontières, labels, repères) sont bien alignées
sur la texture des cartes, et mesure le décalage de longitude éventuel.

Méthode : à 0 Ma, les 242 labels de pays ont des coordonnées réelles. On projette
chacun dans la texture équirectangulaire pour plusieurs décalages de longitude,
et on regarde si le pixel correspondant est de la TERRE (vert/ocre/brun/blanc)
ou de l'OCÉAN (bleu). Le bon décalage maximise le nombre de labels sur terre.

Même test à 460 Ma avec les labels paléo reconstruits.
"""
import json, os, re
from PIL import Image

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
s = open(os.path.join(ICI, "borders_genere.js"), encoding="utf-8").read()
m = re.search(r"const FRONTIERES_PALEO=(\{.*?\});\nconst NOMS_PAYS=", s, re.S)
BORDS = json.loads(m.group(1))
Q = 10.0


def est_terre(rgb):
    r, g, b = rgb[0], rgb[1], rgb[2]
    # Océan : bleu dominant. Terre : vert / ocre / brun / blanc.
    if b > r + 12 and b > g + 6:
        return False
    return True


def tester(annee, chemin_carte):
    im = Image.open(chemin_carte).convert("RGB")
    W, H = im.size
    labels = BORDS[str(annee)]["n"]
    pix = im.load()
    print("\nAnnée", annee, "| carte", os.path.basename(chemin_carte), W, "x", H,
          "| labels", len(labels))
    for decal in (0.0, 0.5, -0.5, 0.25):
        terre = 0
        total = 0
        for nom, la, lo in labels:
            lat, lon = la / Q, lo / Q
            u = (0.5 + lon / 360.0 + decal) % 1.0
            v = 0.5 - lat / 180.0
            if not (0 <= v < 1):
                continue
            x = min(W - 1, int(u * W))
            y = min(H - 1, int(v * H))
            total += 1
            if est_terre(pix[x, y]):
                terre += 1
        print("  décalage {:+.2f} tour ({:+6.1f}°) : {:3d}/{:3d} labels sur terre ({:.0f} %)".format(
            decal, decal * 360, terre, total, 100.0 * terre / max(1, total)))


for annee in (0, 250, 460):
    p = os.path.join(RACINE, "cartes", str(annee) + ".webp")
    if os.path.exists(p):
        tester(annee, p)
    else:
        print("carte absente :", p)

# Contrôle ponctuel : Auriol 460 Ma d'après l'API et le label France 460 Ma
paleo = json.load(open(os.path.join(ICI, "paleo_brut.json"), encoding="utf-8"))
print("\nAuriol 460 Ma (API) :", paleo["460"][str([v[0] for v in json.loads(
    re.search(r"const VILLES=(.*?);\n", open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read(), re.S).group(1))].index("Auriol"))])
print("Auriol 1000 Ma      :", paleo["1000"][str([v[0] for v in json.loads(
    re.search(r"const VILLES=(.*?);\n", open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read(), re.S).group(1))].index("Auriol"))])
