"""Assemble le fichier HTML autonome final à partir du modèle et des données générées."""
import json
import os
import re

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE = os.path.join(OUT, "_outils")


def lire(nom):
    return open(os.path.join(SOURCE, nom), encoding="utf-8").read()


modele = lire("modele.html")
donnees = lire("donnees_generees.js")
cartes = lire("cartes_generees.js")
bords = lire("borders_genere.js")
fiches = lire("fiches_genere.js")
paleo = json.load(open(os.path.join(SOURCE, "paleo_brut.json"), encoding="utf-8"))

# Paléo-coordonnées réelles : 119 dates × 56 villes, null = plaque non reconstructible.
assert len(paleo) == 119, "nombre de dates incorrect : {}".format(len(paleo))
assert sum(len(v) for v in paleo.values()) == 119 * 56, "grille paléo incomplète"
frag_paleo = "const PALEO=" + json.dumps(paleo, separators=(",", ":")) + ";\n"
enrichissements = frag_paleo + bords.rstrip() + "\n" + fiches.rstrip()

for marqueur in ("/*__DONNEES__*/", "/*__CARTES__*/", "/*__ENRICHISSEMENTS__*/"):
    assert marqueur in modele, "marqueur absent : " + marqueur

html = modele.replace("/*__DONNEES__*/", donnees.rstrip())
html = html.replace("/*__CARTES__*/", cartes.rstrip())
html = html.replace("/*__ENRICHISSEMENTS__*/", enrichissements)

cible = os.path.join(OUT, "index.html")
with open(cible, "w", encoding="utf-8", newline="\n") as f:
    f.write(html)

# --- Contrôles de cohérence du livrable ---
assert "__DONNEES__" not in html and "__CARTES__" not in html and "__ENRICHISSEMENTS__" not in html
for nom in ("STEPS", "EPOQUES", "PERIODES", "EVENEMENTS", "VILLES",
            "CARTES", "NUAGES", "FRONTIERES", "PALEO", "FRONTIERES_PALEO",
            "NOMS_PAYS", "DINOS", "FOSSILES_VILLES", "LIBELLES_VILLES", "SITES_FOSSILES"):
    assert re.search(r"const " + nom + r"=", html), nom + " absent"
# Le modèle de plaques simplifié a bien été retiré du livrable.
assert "const PLAQUES=" not in html and "DATES_PLAQUES" not in html, "modèle simplifié encore présent"

externes = re.findall(r'(?:src|href)\s*=\s*["\']https?://[^"\']+', html)
imports = re.findall(r"@import|url\(\s*['\"]?https?://", html)
print("Fichier :", cible)
print("Taille :", round(len(html.encode("utf-8")) / 1024 / 1024, 2), "Mo")
print("Marqueurs restants :", html.count("/*__"))
print("Liens externes (liens de crédit / fiches uniquement) :", len(externes))
print("Ressources externes chargées :", len(imports))
print("Data URLs images :", html.count("data:image/webp;base64,"))
print("Fiches fossiles :", fiches.count('"u":"https://dinosaurpictures.org/'))
