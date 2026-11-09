"""Complète les 851 paires (ville, année) manquantes de paleo_partiel.jsonl.

Le collecteur initial traitait tout HTTPError comme une panne réseau et supprimait
silencieusement la paire. En réalité l'API répond :

    HTTP 404 {"success":false,"error":"Coordinates not found"}

ce qui signifie, comme le dit l'application d'origine, que la plaque tectonique
du point ne remonte pas aussi loin. C'est une DONNÉE (null), pas une erreur.
"""
import json, os, re, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

ICI = os.path.dirname(os.path.abspath(__file__))
donnees = open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read()
STEPS = json.loads(re.search(r"const STEPS=(.*?);\n", donnees, re.S).group(1))
VILLES = json.loads(re.search(r"const VILLES=(.*?);\n", donnees, re.S).group(1))
PARTIEL = os.path.join(ICI, "paleo_partiel.jsonl")
SORTIE = os.path.join(ICI, "paleo_brut.json")

deja = {}
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
statut = {"ok": 0, "404": 0, "erreur": 0}


def un(i, a, v):
    url = "https://dinosaurpictures.org/api/geo-reconstruct/{}?lat={}&lng={}".format(a, v[1], v[2])
    for essai in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (offline-edu)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                obj = json.loads(r.read().decode("utf-8"))
            d = obj.get("data") or {}
            if obj.get("success") and isinstance(d.get("lat"), (int, float)) and isinstance(d.get("lng"), (int, float)):
                return i, a, [round(d["lat"], 2), round(d["lng"], 2)], "ok"
            return i, a, None, "404"       # succès:false sans erreur réseau
        except urllib.error.HTTPError as e:
            # 404 = coordonnées absentes du modèle de plaques à cette date
            if e.code in (404, 400, 422):
                try:
                    e.read()
                except Exception:
                    pass
                return i, a, None, "404"
            if essai == 5:
                return i, a, None, "erreur"
        except Exception:
            if essai == 5:
                return i, a, None, "erreur"
        time.sleep(0.7 * (essai + 1))
    return i, a, None, "erreur"


with ThreadPoolExecutor(max_workers=12) as ex:
    futures = [ex.submit(un, *t) for t in taches]
    for f in as_completed(futures):
        i, a, p, s = f.result()
        with verrou:
            statut[s] += 1
            if s != "erreur":
                deja[(i, a)] = p
                fichier.write(json.dumps({"v": i, "a": a, "p": p}, separators=(",", ":")) + "\n")
            compteur[0] += 1
            if compteur[0] % 200 == 0:
                fichier.flush()
                print("  ...", compteur[0], "/", len(taches), statut, flush=True)
fichier.close()

paleo = {}
for (i, a), p in deja.items():
    paleo.setdefault(str(a), {})[str(i)] = p
with open(SORTIE, "w", encoding="utf-8") as f:
    json.dump(paleo, f, separators=(",", ":"))

ok = sum(1 for a in paleo for p in paleo[a].values() if p)
non = sum(1 for a in paleo for p in paleo[a].values() if p is None)
print("Années :", len(paleo), "| positions :", ok, "| non reconstructibles :", non, flush=True)
print("Statut :", statut, "| taille :", os.path.getsize(SORTIE), "octets", flush=True)
ia = [v[0] for v in VILLES].index("Auriol")
print("Auriol 460 :", paleo.get("460", {}).get(str(ia)), "| 1000 :", paleo.get("1000", {}).get(str(ia)), flush=True)
