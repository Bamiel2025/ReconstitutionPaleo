"""Collecte les paléo-coordonnées RÉELLES (modèle de plaques du site d'origine).

56 villes × 119 pas de temps via /api/geo-reconstruct/<mya>?lat=&lng=.
Reprise possible : les résultats déjà obtenus sont dans paleo_partiel.jsonl.
"""
import json, os, re, threading, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ICI = os.path.dirname(os.path.abspath(__file__))
donnees = open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read()
STEPS = json.loads(re.search(r"const STEPS=(.*?);\n", donnees, re.S).group(1))
VILLES = json.loads(re.search(r"const VILLES=(.*?);\n", donnees, re.S).group(1))
PARTIEL = os.path.join(ICI, "paleo_partiel.jsonl")
SORTIE = os.path.join(ICI, "paleo_brut.json")

deja = {}
if os.path.exists(PARTIEL):
    for ligne in open(PARTIEL, encoding="utf-8"):
        try:
            e = json.loads(ligne)
            deja[(e["v"], e["a"])] = e["p"]
        except Exception:
            pass

taches = [(i, a, v) for i, v in enumerate(VILLES) for a in STEPS
          if (i, a) not in deja]
print("Total", len(VILLES) * len(STEPS), "| déjà", len(deja), "| à faire", len(taches), flush=True)

verrou = threading.Lock()
fichier = open(PARTIEL, "a", encoding="utf-8")
compteur = [0]


def un(i, a, v):
    url = "https://dinosaurpictures.org/api/geo-reconstruct/{}?lat={}&lng={}".format(a, v[1], v[2])
    for essai in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (offline-edu)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                obj = json.loads(r.read().decode("utf-8"))
            d = obj.get("data") or {}
            if obj.get("success") and isinstance(d.get("lat"), (int, float)) and isinstance(d.get("lng"), (int, float)):
                p = [round(d["lat"], 2), round(d["lng"], 2)]
            else:
                p = None
            return i, a, p
        except Exception:
            if essai == 4:
                return i, a, "ERREUR"
            time.sleep(0.8 * (essai + 1))


with ThreadPoolExecutor(max_workers=16) as ex:
    futures = [ex.submit(un, *t) for t in taches]
    for f in as_completed(futures):
        i, a, p = f.result()
        with verrou:
            if p == "ERREUR":
                continue
            deja[(i, a)] = p
            fichier.write(json.dumps({"v": i, "a": a, "p": p}, separators=(",", ":")) + "\n")
            compteur[0] += 1
            if compteur[0] % 500 == 0:
                fichier.flush()
                print("  ...", compteur[0], "/", len(taches), flush=True)
fichier.close()

paleo = {}
for (i, a), p in deja.items():
    paleo.setdefault(str(a), {})[str(i)] = p
with open(SORTIE, "w", encoding="utf-8") as f:
    json.dump(paleo, f, separators=(",", ":"))

annees = [a for a in STEPS if str(a) in paleo]
ok = sum(1 for a in paleo for p in paleo[a].values() if p)
non = sum(1 for a in paleo for p in paleo[a].values() if p is None)
print("Années :", len(annees), "| positions :", ok, "| non reconstructibles :", non, flush=True)
print("Taille :", os.path.getsize(SORTIE), "octets", flush=True)
print("Auriol 460 :", paleo.get("460", {}).get(str([v[0] for v in VILLES].index("Auriol"))), flush=True)
