# -*- coding: utf-8 -*-
"""Assemble les données françaises de l'application à partir du relevé du site."""
import json, os, re
from traductions import (LIBELLES_FR, DESCRIPTIONS_FR, PERIODES_FR,
                         EVENEMENTS_FR, VILLES)

OUT = r"D:/IA/ReconstitutionPaleoTerre/_outils"
page = open(os.path.join(OUT, "page_originale.html"), encoding="utf-8", errors="replace").read()
bundle = open(os.path.join(OUT, "bundle.js"), encoding="utf-8", errors="replace").read()
brut = json.load(open(os.path.join(OUT, "periodes_en.json"), encoding="utf-8"))

# Pas de temps (les 119 premières options = le sélecteur d'année)
options = [int(v) for v in re.findall(r'<option value="(\d+)"', page)]
steps = options[: len(brut)]

# Descriptions : appariement sur la liste triée des textes uniques
textes_uniques = sorted({d["explanation"] for d in brut if d["explanation"]})
assert len(textes_uniques) == len(DESCRIPTIONS_FR) == 56, "Nombre de descriptions incohérent"
trad_texte = dict(zip(textes_uniques, DESCRIPTIONS_FR))

epoques = {}
for d in brut:
    en = d["label"]
    assert en in LIBELLES_FR, "Libellé non traduit : " + en
    epoques[str(d["mya"])] = {
        "l": LIBELLES_FR[en],
        "t": trad_texte.get(d["explanation"], ""),
        "s": d["source"],
    }
assert len(epoques) == 119

# Périodes géologiques de la frise
periode_bloc = re.search(r"var PERIODS=\[(.*?)\];var LIGHT_TEXT", bundle, re.S).group(1)
periodes = []
for m in re.finditer(r'\{name:"([^"]+)",abbr:"([^"]*)",start:([\d.e]+),end:([\d.e]+),color:"(#[0-9A-Fa-f]{6})"\}', periode_bloc):
    nom_en, abbr_en, start, end, color = m.groups()
    nom_fr, abbr_fr = PERIODES_FR[nom_en]
    periodes.append({"n": nom_fr, "a": abbr_fr, "d": float(start), "f": float(end),
                     "c": color, "clair": nom_en in ("Ordovician", "Triassic", "Permian")})
assert len(periodes) == 15, len(periodes)

# Événements : options du menu « Jump to… »
menu = re.search(r'<select id="jump-to".*?</select>', page, re.S).group(0)
evenements = []
for v, nom in re.findall(r'<option value="(\d+)">([^<]+)</option>', menu):
    evenements.append({"m": int(v), "n": EVENEMENTS_FR[nom.strip()]})
assert len(evenements) == 22, len(evenements)

with open(os.path.join(OUT, "donnees_generees.js"), "w", encoding="utf-8") as f:
    f.write("const STEPS=" + json.dumps(steps, separators=(",", ":")) + ";\n")
    f.write("const EPOQUES=" + json.dumps(epoques, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("const PERIODES=" + json.dumps(periodes, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("const EVENEMENTS=" + json.dumps(evenements, ensure_ascii=False, separators=(",", ":")) + ";\n")
    f.write("const VILLES=" + json.dumps(VILLES, ensure_ascii=False, separators=(",", ":")) + ";\n")

print("Époques :", len(epoques), "| Périodes :", len(periodes), "| Événements :", len(evenements),
      "| Villes :", len(VILLES))
print("Vérif 460 Ma :", epoques["460"])
print("Vérif 0 Ma :", epoques["0"])
