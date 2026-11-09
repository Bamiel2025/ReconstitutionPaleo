"""Constitue les fiches de fossiles : faits du site, texte français, photo Commons.

Version reprenable (checkpoint) + conservatrice (3 workers, backoff 429).
Ne récupère QUE les taxons incomplets (sans image OU sans texte) si un
fiches_genere.js existe déjà ; relance sans perte les taxons manquants.

N'utilise PAS les illustrations générées par IA du site d'origine (signalées
pouvant être scientifiquement inexactes). Images depuis Wikimedia Commons
(vignette Wikipédia FR, puis EN, puis recherche Commons), attribution groupée.
"""
import base64, html, io, json, os, re, time, urllib.error, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

# --- Robustesse chemin : Git Bash /x/ -> X:/ pour le Python Windows ---
def norm(p):
    m = re.match(r"^/([a-z])/(.*)$", p)
    return (m.group(1).upper() + ":/" + m.group(2)) if m else p

ICI = norm(os.path.dirname(os.path.abspath(__file__)))
UA = {"User-Agent": "Mozilla/5.0 (compatible; LinnEdu/1.0; offline teaching application)"}
fossiles = json.load(open(os.path.join(ICI, "fossiles_brut.json"), encoding="utf-8"))
donnees = open(os.path.join(ICI, "donnees_generees.js"), encoding="utf-8").read()
VILLES = json.loads(re.search(r"const VILLES=(.*?);\n", donnees, re.S).group(1))

noms = sorted({n for d in fossiles.values()
               for n in ((d.get("data") or {}).get("nearby") or {}).get("names", [])})
print("Genres :", len(noms), flush=True)

REGIME = {
    "herbivore": "herbivore", "carnivore": "carnivore", "omnivore": "omnivore",
    "piscivore": "piscivore", "insectivore": "insectivore", "durophagous": "durophage",
    "filter-feeder": "filtreur", "planktivore": "planctonivore",
}
PERIODE = {
    "Cretaceous": "Crétacé", "Late Cretaceous": "Crétacé supérieur",
    "Early Cretaceous": "Crétacé inférieur", "Jurassic": "Jurassique",
    "Late Jurassic": "Jurassique supérieur", "Middle Jurassic": "Jurassique moyen",
    "Early Jurassic": "Jurassique inférieur", "Triassic": "Trias",
    "Late Triassic": "Trias supérieur", "Permian": "Permien",
    "Devonian": "Dévonien", "Carboniferous": "Carbonifère",
    "Paleogene": "Paléogène", "Neogene": "Néogène", "Eocene": "Éocène",
    "Miocene": "Miocène", "Pleistocene": "Pléistocène", "Silurian": "Silurien",
}
REGION = {
    "Europe": "Europe", "North America": "Amérique du Nord",
    "South America": "Amérique du Sud", "Africa": "Afrique", "Asia": "Asie",
    "Australia": "Australie", "Antarctica": "Antarctique",
    "Madagascar": "Madagascar", "India": "Inde", "New Zealand": "Nouvelle-Zélande",
}
PAYS = {
    "Spain": "Espagne", "France": "France", "Germany": "Allemagne",
    "United States": "États-Unis", "United Kingdom": "Royaume-Uni", "Canada": "Canada",
    "China": "Chine", "Argentina": "Argentine", "Romania": "Roumanie",
    "Portugal": "Portugal", "Morocco": "Maroc", "Mongolia": "Mongolie",
    "South Africa": "Afrique du Sud", "Australia": "Australie", "India": "Inde",
    "Brazil": "Brésil", "Russia": "Russie", "Italy": "Italie", "Belgium": "Belgique",
    "Switzerland": "Suisse", "Austria": "Autriche", "Poland": "Pologne",
    "Tanzania": "Tanzanie", "Egypt": "Égypte", "Mexico": "Mexique",
    "Japan": "Japon", "Niger": "Niger", "Netherlands": "Pays-Bas",
}


def get(url, timeout=30, essais=6):
    for k in range(essais):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            if k == essais - 1:
                raise
            time.sleep(2.5 * (k + 1) if e.code == 429 else 0.8 * (k + 1))
        except Exception:
            if k == essais - 1:
                raise
            time.sleep(0.8 * (k + 1))
    raise RuntimeError("épuisé")


def json_get(url):
    return json.loads(get(url).decode("utf-8", "replace"))


def nettoyer(t):
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip()


def deux_phrases(t, limite=330):
    t = nettoyer(t)
    if not t:
        return ""
    premier = t.find(". ")
    coup = t.find(". ", premier + 2) if premier >= 0 else -1
    if coup > 0:
        t = t[:coup + 1]
    if len(t) > limite:
        t = t[:limite].rsplit(" ", 1)[0] + "…"
    return t


def traduire_gisements(g):
    g = nettoyer(g)
    g = re.sub(r"\s+,\s*", ", ", g)
    g = re.sub(r"\s+and\s+", " et ", g)
    for en, fr in PAYS.items():
        g = re.sub(r"\b" + re.escape(en) + r"\b", fr, g)
    return g.rstrip(" .")[:180]


def phrase_depuis_faits(f):
    if not (f["regime"] or f["periode"] or f["region"]):
        return ""
    s = "Taxon fossile"
    if f["regime"]:
        s += " " + f["regime"]
    if f["periode"]:
        s += " du " + f["periode"]
    if f["region"]:
        s += ", connu en " + f["region"]
    s += "."
    if f["g"]:
        s += " Ses fossiles ont été signalés à " + traduire_gisements(f["g"]) + "."
    return s


def titre_fichier(src):
    for seg in urllib.parse.urlparse(src).path.split("/"):
        if re.search(r"\.(jpg|jpeg|png|webp|gif|tif|tiff)$", seg, re.I):
            return urllib.parse.unquote(seg)
    return ""


def sources_image(nom):
    """Vignettes Wikipédia FR/EN puis recherche Commons (jamais les images IA du site)."""
    out = []
    for lang in ("fr", "en"):
        try:
            d = json_get("https://" + lang + ".wikipedia.org/api/rest_v1/page/summary/"
                         + urllib.parse.quote(nom))
            src = (d.get("thumbnail") or {}).get("source") or (d.get("originalimage") or {}).get("source")
            if src and not src.lower().endswith(".svg"):
                out.append(src)
        except Exception:
            pass
    try:
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&generator=search&gsrnamespace=6&gsrlimit=6&prop=imageinfo"
               "&iiprop=url|mime&iiurlwidth=420&gsrsearch=" + urllib.parse.quote(nom))
        d = json_get(api)
        for p in (d.get("query", {}).get("pages", {}) or {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            u = ii.get("thumburl") or ii.get("url")
            if u and not u.lower().endswith(".svg") and ii.get("mime", "image/").startswith("image/"):
                out.append(u)
    except Exception:
        pass
    return out[:8]


def encoder_image(octets):
    im = Image.open(io.BytesIO(octets))
    if "A" in im.getbands() or im.mode == "P":
        im = im.convert("RGBA")
    else:
        im = im.convert("RGB")
    im.thumbnail((360, 240), Image.LANCZOS)
    fond = Image.new("RGB", im.size, (255, 255, 255))
    if im.mode == "RGBA":
        fond.paste(im, mask=im.getchannel("A"))
    else:
        fond.paste(im)
    buf = io.BytesIO()
    fond.save(buf, "WEBP", quality=64, method=5)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def un_fiche(nom):
    page = "https://dinosaurpictures.org/" + urllib.parse.quote(nom) + "-pictures"
    fait = {"regime": "", "periode": "", "region": "", "gisements": ""}
    try:
        s = get(page).decode("utf-8", "replace")
        s = re.sub(r"<script.*?</script>", " ", s, flags=re.S)
        s = re.sub(r"<style.*?</style>", " ", s, flags=re.S)
        t = nettoyer(re.sub(r"<[^>]+>", " ", s))
        m = re.search(r"\bwas an? ([A-Za-z-]+)\s*\.", t)
        if m:
            fait["regime"] = REGIME.get(m.group(1).lower(), "")
        m = re.search(r"lived in the ([A-Za-z ]+?) period", t)
        if m:
            fait["periode"] = PERIODE.get(m.group(1).strip(), m.group(1).strip())
        m = re.search(r"inhabited ([A-Za-z ]+?)\s*\.", t)
        if m:
            r = m.group(1).strip()
            fait["region"] = REGION.get(r, r)
        m = re.search(r"fossils have been found in places such as (.*?)\s*\.\s", t)
        if m:
            fait["gisements"] = nettoyer(m.group(1))[:180]
    except Exception:
        pass

    resume_fr = ""
    try:
        d = json_get("https://fr.wikipedia.org/api/rest_v1/page/summary/" + urllib.parse.quote(nom))
        if d.get("type") == "standard":
            resume_fr = deux_phrases(d.get("extract", ""))
    except Exception:
        pass

    # Le téléchargement de l'image est indépendant de l'attribution :
    # un échec de l'API Commons ne doit JAMAIS effacer une photo déjà obtenue.
    image, fichier = "", ""
    for src in sources_image(nom):
        try:
            image = encoder_image(get(src, timeout=40))
            fichier = titre_fichier(src)
            if image:
                break
        except Exception:
            continue

    return nom, {
        "n": nom, "u": page, "r": fait["regime"], "p": fait["periode"],
        "z": fait["region"], "g": traduire_gisements(fait["gisements"]),
        "t": resume_fr or phrase_depuis_faits(fait), "i": image, "c": "",
    }, fichier


# --- Reprise sur fiches_genere.js existant ---
def charger_existants():
    try:
        s = open(os.path.join(ICI, "fiches_genere.js"), encoding="utf-8").read()
        g = {}
        for nom_c in ("DINOS", "FOSSILES_VILLES", "LIBELLES_VILLES", "SITES_FOSSILES"):
            m = re.search(r"const " + nom_c + r"=(\{.*?\});\n", s, re.S)
            if m:
                g[nom_c] = json.loads(m.group(1))
        return g
    except Exception:
        return {}


ex = charger_existants()
dinos = dict(ex.get("DINOS", {}))
par_ville = dict(ex.get("FOSSILES_VILLES", {}))
libelles = dict(ex.get("LIBELLES_VILLES", {}))
sites = dict(ex.get("SITES_FOSSILES", {}))
# Les noms de fichiers Commons ne sont pas récupérables depuis l'image base64 :
# on laisse `fichiers` vide. Les crédits des images reprises depuis l'ancien
# fichier restent ceux déjà présents dans `d.c` (génériques si absents).
fichiers = {}


def complet(nom):
    d = dinos.get(nom)
    return bool(d and d.get("i") and d.get("t"))


a_faire = [n for n in noms if not complet(n)]
print("Déjà complets :", len(noms) - len(a_faire), "| à faire :", len(a_faire), flush=True)


# --- Attribution groupée (3 requêtes au lieu de 104) ---
def lots(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def sauver():
    with open(os.path.join(ICI, "fiches_genere.js"), "w", encoding="utf-8") as f:
        f.write("const DINOS=" + json.dumps(dinos, ensure_ascii=False, separators=(",", ":")) + ";\n")
        f.write("const FOSSILES_VILLES=" + json.dumps(par_ville, ensure_ascii=False, separators=(",", ":")) + ";\n")
        f.write("const LIBELLES_VILLES=" + json.dumps(libelles, ensure_ascii=False, separators=(",", ":")) + ";\n")
        f.write("const SITES_FOSSILES=" + json.dumps(sites, ensure_ascii=False, separators=(",", ":")) + ";\n")


# Données villes (réseau uniquement pour LIBELLES ; FOSSILES/SITES depuis le brut)
if not par_ville or not sites:
    for ville, d in fossiles.items():
        near = (d.get("data") or {}).get("nearby") or {}
        par_ville[ville] = near.get("names", [])
        sites[ville] = {n: [[round(p[0], 3), round(p[1], 3)] for p in pts]
                        for n, pts in (near.get("lookup") or {}).items()}

if not libelles:
    def ville(v):
        try:
            d = json_get("https://dinosaurpictures.org/api/geocode/" + urllib.parse.quote(v[0]))
            return v[0], (d.get("data") or {}).get("name", v[0])
        except Exception:
            return v[0], v[0]
    with ThreadPoolExecutor(max_workers=3) as ex2:
        for n, l in ex2.map(ville, VILLES):
            libelles[n] = l

# --- Boucle reprenable par lots de 12, 3 workers ---
BATCH = 12
def un_fiche_sur(nom):
    try:
        return un_fiche(nom)
    except Exception as e:
        return nom, {"n": nom, "u": "https://dinosaurpictures.org/" + urllib.parse.quote(nom) + "-pictures",
                     "r": "", "p": "", "z": "", "g": "", "t": "", "i": "", "c": ""}, ""

for debut in range(0, len(a_faire), BATCH):
    lot = a_faire[debut:debut + BATCH]
    with ThreadPoolExecutor(max_workers=3) as ex2:
        for nom, d, titre in ex2.map(un_fiche_sur, lot):
            dinos[nom] = d
            if titre:
                fichiers[nom] = titre
    sauver()  # checkpoint
    print("  checkpoint", min(debut + BATCH, len(a_faire)), "/", len(a_faire),
          "| photos:", sum(1 for d in dinos.values() if d["i"]), flush=True)

# --- Attribution groupée finale ---
credits = {}
cles = sorted(set(fichiers.values()))
for lot in lots(cles, 40):
    try:
        api = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&prop=imageinfo&iiprop=extmetadata&titles="
               + urllib.parse.quote("|".join("File:" + t for t in lot)))
        meta = json_get(api)
        for p in (meta.get("query", {}).get("pages", {}) or {}).values():
            ii = (p.get("imageinfo") or [{}])[0]
            em = ii.get("extmetadata") or {}
            art = nettoyer(re.sub(r"<[^>]+>", "", em.get("Artist", {}).get("value", "")))[:70]
            lic = em.get("LicenseShortName", {}).get("value", "")
            titre = p.get("title", "").replace("File:", "").replace("_", " ")
            credits[titre.lower()] = (art + " · " if art else "") + (lic or "Wikimedia Commons")
    except Exception:
        pass
for n, d in dinos.items():
    t = fichiers.get(n, "")
    if t and d["i"]:
        d["c"] = credits.get(t.lower().replace("_", " "), "Wikimedia Commons")

sauver()
print("Fiches :", len(dinos), "| avec photo :", sum(1 for d in dinos.values() if d["i"]), flush=True)
print("Avec texte FR :", sum(1 for d in dinos.values() if d["t"]),
      "| avec faits :", sum(1 for d in dinos.values() if d["r"] or d["p"]), flush=True)
print("Crédits résolus :", sum(1 for d in dinos.values() if d["c"] and d["c"] != "Wikimedia Commons"), flush=True)
print("Libellés villes :", len(libelles), "| taille JS :",
      os.path.getsize(os.path.join(ICI, "fiches_genere.js")), "octets", flush=True)
print("Auriol :", par_ville.get("Auriol"), "| Hypselosaurus image :",
      bool(dinos.get("Hypselosaurus", {}).get("i")), flush=True)
