"""Collecte les listes de fossiles « à proximité » pour les 56 villes via l'API réelle."""
import json, os, re, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ICI = os.path.dirname(os.path.abspath(__file__))
donnees = open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read()
VILLES = json.loads(re.search(r"const VILLES=(.*?);\n", donnees, re.S).group(1))
BASE = "https://dinosaurpictures.org/api/geo-reconstruct/0?lat={}&lng={}"


def chercher(v):
    url = BASE.format(v[1], v[2])
    for essai in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (offline-edu)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return v[0], json.loads(r.read().decode("utf-8"))
        except Exception as e:
            if essai == 3:
                return v[0], {"erreur": str(e)}
            time.sleep(1 + essai)


resultats = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    futures = [ex.submit(chercher, v) for v in VILLES]
    for f in as_completed(futures):
        nom, data = f.result()
        resultats[nom] = data

noms = set()
for nom, data in resultats.items():
    d = data.get("data") or {}
    near = d.get("nearby") or {}
    noms.update(near.get("names") or [])

with open(os.path.join(ICI, "fossiles_brut.json"), "w", encoding="utf-8") as f:
    json.dump(resultats, f, ensure_ascii=False, separators=(",", ":"))

print("Villes interrogées :", len(resultats))
print("Villes avec fossiles :", sum(1 for d in resultats.values()
                                    if (d.get("data") or {}).get("nearby", {}).get("names")))
print("Erreurs :", [k for k, d in resultats.items() if "erreur" in d])
print("Genres distincts :", len(noms))
print("Exemples :", sorted(noms)[:30])
print("Auriol :", (resultats.get("Auriol", {}).get("data") or {}).get("nearby", {}).get("names"))
