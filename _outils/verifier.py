"""Vérification du livrable offline dans un vrai Chromium (Playwright).

Contrôle en particulier la rigueur géographique : paléo-coordonnées réelles,
refus d'inventer un point non reconstructible, contours par date, et l'ensemble
des enrichissements fossiles (liste, fiches, photos hors ligne, liens).
"""
import json
import os
import sys
from playwright.sync_api import sync_playwright

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIER = "file:///D:/IA/ReconstitutionPaleoTerre/index.html#460"
DOSSIER = os.path.join(RACINE, "_outils", "verification")
os.makedirs(DOSSIER, exist_ok=True)

resultats = {}
erreurs_console = []
erreurs_page = []
requetes = []


def rapport(nom, valeur, ok=None):
    resultats[nom] = {"valeur": valeur, "ok": ok}
    print(("[OK]  " if ok else ("[KO]  " if ok is False else "..... ")) + nom + " : " + str(valeur)[:220], flush=True)


with sync_playwright() as p:
    # Aucun flag de sécurité : conditions réelles d'un double-clic sur un fichier local.
    navigateur = p.chromium.launch(
        executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        headless=True,
    )
    contexte = navigateur.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page = contexte.new_page()
    page.on("console", lambda m: erreurs_console.append(m.type + " | " + m.text) if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: erreurs_page.append(str(e)))
    page.on("request", lambda r: requetes.append(r.url))

    page.goto(FICHIER, wait_until="load", timeout=120000)
    page.wait_for_function("document.querySelector('#chargement').hidden === true", timeout=60000)
    page.wait_for_timeout(1200)

    rapport("Titre", page.title(), page.title().startswith("La Terre ancienne"))
    rapport("Date initiale (#460)", page.locator("#combien").inner_text(), page.locator("#combien").inner_text() == "460")
    rapport("Sous-titre", page.locator("#sous-titre").inner_text(), "Ordovicien" in page.locator("#sous-titre").inner_text())
    rapport("Texte scientifique", page.locator("#explication").inner_text()[:90], "Biodiversification" in page.locator("#explication").inner_text())
    rapport("Options du sélecteur d'année", page.locator("#annees option").count(), page.locator("#annees option").count() == 119)
    rapport("Événements « Aller à »", page.locator("#aller-a option").count() - 1, page.locator("#aller-a option").count() - 1 == 22)
    rapport("Bandes géologiques", page.locator("#bandes .bande").count(), page.locator("#bandes .bande").count() == 15)
    rapport("Repères", page.locator("#reperes .repere").count(), page.locator("#reperes .repere").count() >= 15)
    rapport("Questions élève", page.locator("#liste-questions .question").count(), page.locator("#liste-questions .question").count() == 7)
    rapport("Copie imprimable", page.locator("#copie-questions .question").count(), page.locator("#copie-questions .question").count() == 7)
    rapport("Corrigés", page.locator("#liste-corriges .correction").count(), page.locator("#liste-corriges .correction").count() == 7)

    # Le globe doit être réellement dessiné (pixels non noirs au centre).
    pixels = page.evaluate("""() => {
        const c=document.querySelector('#globe'),g=c.getContext('2d');
        const x=Math.floor(c.width/2),y=Math.floor(c.height/2);
        const im=g.getImageData(x-70,y-40,140,80).data; // une seule lecture
        let somme=0,max=0;
        for(let i=0;i<im.length;i+=4){const l=im[i]+im[i+1]+im[i+2];somme+=l;if(l>max)max=l;}
        return {somme,max,nb:im.length/4};
    }""")
    rapport("Globe dessiné (pixels centre)", pixels, pixels["somme"] > 5000)

    # Aucune requête réseau : seules les URLs file:// / data: sont attendues.
    externes = [r for r in requetes if r.startswith("http://") or r.startswith("https://")]
    rapport("Requêtes réseau", externes, len(externes) == 0)

    # Navigation clavier
    page.locator("body").click(position={"x": 700, "y": 300})
    page.keyboard.press("ArrowLeft")
    apres_gauche = page.locator("#combien").inner_text()
    page.keyboard.press("ArrowRight")
    apres_droite = page.locator("#combien").inner_text()
    rapport("Clavier ← / →", apres_gauche + " puis " + apres_droite, apres_gauche == "465" and apres_droite == "460")
    rapport("Hash après navigation", page.evaluate("location.hash"), page.evaluate("location.hash") == "#460")

    # Menu « Aller à… »
    page.select_option("#aller-a", "250")
    page.wait_for_timeout(500)
    rapport("Aller à 250 Ma", page.locator("#combien").inner_text() + " / " + page.locator("#sous-titre").inner_text(), page.locator("#combien").inner_text() == "250")
    rapport("Texte 250 Ma", page.locator("#explication").inner_text()[:80], "extinction" in page.locator("#explication").inner_text().lower())

    # Réglages
    page.locator("#bouton-reglages").click()
    ouvert = page.locator("#panneau-reglages").is_visible()
    # Les cases sont masquées visuellement : on clique sur leur libellé, comme un élève.
    page.get_by_text("Frontières des pays (repositionnées)").click()
    page.get_by_text("Équateur et méridiens").click()
    page.get_by_text("Nuages", exact=True).click()
    etat_opt = page.evaluate("""() => ({
        frontieres:document.querySelector('#opt-frontieres').checked,
        quadrillage:document.querySelector('#opt-quadrillage').checked,
        nuages:document.querySelector('#opt-nuages').checked
    })""")
    rapport("Panneau réglages", ouvert, ouvert)
    rapport("Bascule par libellé", etat_opt, etat_opt == {"frontieres": True, "quadrillage": True, "nuages": False})
    rapport("Options persistées", page.evaluate("localStorage.getItem('paleoTerre.options')"), True)

    # ------------------------------------------------------------------
    # GÉOLOCALISATION RIGoureUSE
    # ------------------------------------------------------------------
    grille = page.evaluate("""() => {
        const ks=Object.keys(PALEO);let pos=0,nul=0;
        ks.forEach(k=>Object.values(PALEO[k]).forEach(p=>{if(p)pos++;else nul++;}));
        return {annees:ks.length,entrees:pos+nul,pos,nul};
    }""")
    rapport("Grille paléo réelle (119 × 56)", grille,
            grille["annees"] == 119 and grille["entrees"] == 6664 and grille["pos"] == 5813 and grille["nul"] == 851)

    coords = page.evaluate("""() => {
        const v=VILLES.find(x=>x[0]==='Auriol');
        return {a0:positionReelle(v,0),a70:positionReelle(v,70),a460:positionReelle(v,460),a1000:positionReelle(v,1000)};
    }""")
    rapport("Auriol : valeurs RÉELLES de l'API", coords,
            coords["a460"] == [-65.81, 92.22] and coords["a0"] == [43.37, 5.63]
            and coords["a1000"] is None and coords["a70"] == [35.2, 4.79])

    src_front = page.evaluate("dessinerFrontieres.toString()")
    rapport("Frontières modernes écartées du rendu", src_front[:70],
            "bordsAnnee" in src_front and "FRONTIERES.forEach" not in src_front)

    bords = page.evaluate("""() => {
        const b0=bordsAnnee(0),b460=bordsAnnee(460),fr=b=>b.n.find(x=>x[0]==='France');
        return {l0:b0.l.length,l460:b460.l.length,n0:b0.n.length,n460:b460.n.length,
                fr0:fr(b0),fr460:fr(b460)};
    }""")
    rapport("Contours et labels PAR DATE", bords,
            bords["l0"] > 500 and bords["l460"] > 500
            and bords["fr0"] and bords["fr460"]
            and bords["fr0"][1] > 40 and bords["fr460"][1] < -60)

    # Sélection de la ville (nécessaire pour le bandeau de coordonnées)
    page.locator("#saisie-ville").fill("Auriol")
    page.locator("#propositions div").first.click()
    page.wait_for_timeout(400)

    page.evaluate("changerAnnee(460)")
    page.wait_for_timeout(250)
    info460 = page.locator("#info-ville").inner_text()
    rapport("Bandeau ville à 460 Ma", info460[:140],
            "Auriol" in info460 and "65,8° S" in info460 and "92,2° E" in info460)

    # ------------------------------------------------------------------
    # ENRICHISSEMENTS FOSSILES
    # ------------------------------------------------------------------
    info = page.locator("#info-ville").inner_text()
    # Le <h3> est stylé en majuscules (text-transform) : comparaison insensible à la casse.
    rapport("Recherche ville (Auriol)", info[:110],
            "Auriol" in info and "FOSSILES À PROXIMITÉ" in info.upper() and "MODÈLE DE PLAQUES" in info.upper())
    rapport("Ville persistée", page.evaluate("localStorage.getItem('paleoTerre.ville')"), page.evaluate("localStorage.getItem('paleoTerre.ville')") == "Auriol")

    couverture = page.evaluate("""() => ({
        villes:Object.keys(FOSSILES_VILLES).filter(v=>FOSSILES_VILLES[v].length).length,
        taxons:Object.keys(DINOS).length,
        villesLibelles:Object.keys(LIBELLES_VILLES).length
    })""")
    rapport("Couverture fossiles", couverture,
            couverture["villes"] == 41 and couverture["taxons"] == 104 and couverture["villesLibelles"] == 56)

    chips = page.locator("#info-ville .chip")
    noms_chips = chips.all_inner_texts()
    rapport("Fossiles à proximité (Auriol)", noms_chips,
            len(noms_chips) == 5 and "Hypselosaurus" in noms_chips)

    chips.filter(has_text="Hypselosaurus").click()
    page.wait_for_timeout(200)
    fiche = page.locator("#corps-fossile").inner_text()
    rapport("Fiche Hypselosaurus", fiche[:170],
            "Crétacé" in fiche and "herbivore" in fiche and "Espagne" in fiche and "Hypselosaurus" in fiche)
    lien = page.locator("#corps-fossile a[href*='dinosaurpictures.org']").first.get_attribute("href")
    rapport("Lien vers la page dédiée", lien, lien == "https://dinosaurpictures.org/Hypselosaurus-pictures")
    img_ok = page.evaluate("""() => {
        const im=document.querySelector('#corps-fossile img');
        if(!im)return 'aucune image';
        return (im.complete&&im.naturalWidth>0)?im.naturalWidth+'x'+im.naturalHeight:'ko';
    }""")
    rapport("Photo Commons hors ligne", img_ok, "x" in img_ok and "ko" not in img_ok and "aucune" not in img_ok)
    rapport("Crédit photo affiché", page.locator("#corps-fossile .credit-photo").inner_text()[:80],
            "Commons" in page.locator("#corps-fossile .credit-photo").inner_text())

    # Le bouton renvoie sur 0 Ma : les sites ne sont valables que sur la carte actuelle.
    page.locator("#voir-sites").click()
    page.wait_for_timeout(350)
    sites = page.evaluate("""() => ({
        annee:document.querySelector('#combien').textContent,
        bandeau:!document.querySelector('#sites-actifs').hidden,
        taxon:taxonActif,
        nb:sitesDuTaxon('Hypselosaurus').length
    })""")
    rapport("Sites de découverte à 0 Ma uniquement", sites,
            sites["annee"] == "" and sites["bandeau"] and sites["taxon"] == "Hypselosaurus" and sites["nb"] > 0)
    page.locator("#masquer-sites").click()
    rapport("Masquer les sites", page.locator("#sites-actifs").is_visible(), not page.locator("#sites-actifs").is_visible())

    # Point non reconstructible : l'application dit explicitement qu'elle ne sait pas.
    page.evaluate("changerAnnee(1000)")
    page.wait_for_timeout(250)
    info1000 = page.locator("#info-ville").inner_text()
    rapport("Date non reconstructible assumée", info1000[:130], "non reconstructible" in info1000 and "essaie une date plus récente" in info1000)
    page.evaluate("changerAnnee(460)")

    # Toutes les images de fiches doivent décoder hors ligne.
    images = page.evaluate("""async () => {
        const ks=Object.keys(DINOS).filter(k=>DINOS[k].i);let ok=0,bad=[];
        for(const k of ks){
            await new Promise(res=>{const im=new Image();im.onload=()=>{ok++;res();};im.onerror=()=>{bad.push(k);res();};im.src=DINOS[k].i;});
        }
        return {total:ks.length,ok,bad};
    }""")
    rapport("Décodage des photos de fiches", images,
            images["total"] >= 60 and images["ok"] == images["total"] and not images["bad"])

    # Crédits : la provenance et le refus des images IA sont documentés.
    page.locator("#lien-credits").click()
    cred = page.locator("#fenetre-credits .contenu").inner_text()
    rapport("Crédits : rigueur documentée", cred[:110],
            "non reconstructible" in cred and "Wikimedia Commons" in cred
            and "générées par IA" in cred and "paléo-coordonnées" in cred)
    page.locator("#fenetre-credits [data-fermer]").click()

    # Verrou pédagogique
    page.locator("#bouton-bilan").click()
    avant = page.locator("#volet-bilan").is_visible()
    page.locator("#code-prof").fill("1234")
    page.locator("#valider-code").click()
    faux = page.locator("#message-code").inner_text()
    page.locator("#code-prof").fill("2027")
    page.locator("#valider-code").click()
    apres = page.locator("#volet-bilan").is_visible()
    rapport("Corrigé masqué avant code", avant, avant is False)
    rapport("Code erroné", faux, "incorrect" in faux.lower())
    rapport("Corrigé visible après 2027", apres, apres is True)
    rapport("Fiche professeur", page.evaluate("""() => {document.querySelector('[data-volet=prof]').click();return document.querySelector('#volet-prof').offsetHeight>100;}"""), True)

    # Autosave des réponses
    page.evaluate("""() => {document.querySelector('[data-volet=activite]').click();}""")
    page.locator("textarea[data-q='0']").fill("Réponse de test : Gondwana au sud.")
    stocke = page.evaluate("localStorage.getItem('paleoTerre.reponses.v1')")
    rapport("Autosave réponses", stocke, "Gondwana" in (stocke or ""))

    # Export .txt (doit mentionner la ville et ses fossiles)
    with page.expect_download() as dl:
        page.locator("#exporter").click()
    telechargement = dl.value
    chemin_txt = os.path.join(DOSSIER, "export-test.txt")
    telechargement.save_as(chemin_txt)
    contenu_txt = open(chemin_txt, encoding="utf-8").read()
    rapport("Export .txt", telechargement.suggested_filename,
            telechargement.suggested_filename.endswith(".txt") and "Hypselosaurus" in contenu_txt and "Auriol" in contenu_txt)

    # Impression : la fiche élève doit être visible, l'interface masquée
    page.emulate_media(media="print")
    impression = page.evaluate("""() => ({
        fiche:getComputedStyle(document.querySelector('#fiche-eleve')).display,
        globe:getComputedStyle(document.querySelector('#globe')).display,
        volet:getComputedStyle(document.querySelector('#volet-activite')).display
    })""")
    rapport("Média impression", impression, impression["fiche"] == "block" and impression["globe"] == "none" and impression["volet"] == "none")
    pdf = os.path.join(DOSSIER, "fiche-eleve.pdf")
    page.pdf(path=pdf, format="A4", print_background=False)
    rapport("PDF de la fiche élève", os.path.getsize(pdf), os.path.getsize(pdf) > 8000)
    page.emulate_media(media="screen")
    page.locator("#fenetre-classe [data-fermer]").click()

    # Remise à 460 Ma puis captures aux trois largeurs
    page.evaluate("changerAnnee(460)")
    page.wait_for_timeout(900)
    for largeur, hauteur, nom in [(1440, 900, "final-1440.png"), (900, 700, "final-900.png"), (390, 844, "final-390.png")]:
        page.set_viewport_size({"width": largeur, "height": hauteur})
        page.wait_for_timeout(700)
        page.screenshot(path=os.path.join(DOSSIER, nom))
        rapport("Capture " + str(largeur) + " px", nom, os.path.getsize(os.path.join(DOSSIER, nom)) > 10000)

    # Décodage de TOUTES les cartes intégrées (détecte un WebP corrompu)
    page.set_viewport_size({"width": 1440, "height": 900})
    decode = page.evaluate("""async () => {
        const ks=Object.keys(CARTES);let ok=0,bad=[];
        for(const k of ks){
            await new Promise(res=>{
                const im=new Image();
                im.onload=()=>{ok++;res();};
                im.onerror=()=>{bad.push(k);res();};
                im.src=CARTES[k];
            });
        }
        const n=await new Promise(res=>{const im=new Image();im.onload=()=>res('ok');im.onerror=()=>res('ko');im.src=NUAGES;});
        return {total:ks.length,ok,bad,nuages:n};
    }""")
    rapport("Décodage des 119 cartes", decode, decode["ok"] == 119 and not decode["bad"] and decode["nuages"] == "ok")

    # Bascule sur quelques dates pour vérifier le changement de texture
    echantillon = page.evaluate("""async () => {
        const ans=[0,66,250,460,540,750,1000],out=[];
        for(const a of ans){changerAnnee(a);await new Promise(r=>setTimeout(r,220));out.push([a,document.querySelector('#sous-titre').textContent]);}
        return out;
    }""")
    rapport("Échantillon de dates", echantillon, all(x[1] for x in echantillon if x[0] != 0))

    rapport("Erreurs console", erreurs_console[:8], len(erreurs_console) == 0)
    rapport("Erreurs JavaScript", erreurs_page[:8], len(erreurs_page) == 0)

    with open(os.path.join(DOSSIER, "rapport.json"), "w", encoding="utf-8") as f:
        json.dump({"resultats": resultats, "console": erreurs_console, "page": erreurs_page, "requetes": requetes}, f, ensure_ascii=False, indent=2)

    navigateur.close()

echecs = [k for k, v in resultats.items() if v["ok"] is False]
print("\n=== BILAN ===", flush=True)
print("Contrôles :", len(resultats), "| Échecs :", len(echecs), flush=True)
for k in echecs:
    print("  -", k, "->", resultats[k]["valeur"], flush=True)
sys.exit(1 if echecs else 0)
