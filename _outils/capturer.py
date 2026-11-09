"""Captures « état propre » du livrable pour comparaison avec l'original."""
import os
from playwright.sync_api import sync_playwright

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "verification")
os.makedirs(DOSSIER, exist_ok=True)
URL = "file:///D:/IA/ReconstitutionPaleoTerre/index.html#460"

with sync_playwright() as p:
    nav = p.chromium.launch(executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe", headless=True)
    for largeur, hauteur, suffixe in [(1440, 900, "1440"), (900, 700, "900"), (390, 844, "390")]:
        ctx = nav.new_context(viewport={"width": largeur, "height": hauteur}, device_scale_factor=1)
        page = ctx.new_page()
        page.goto(URL, wait_until="load", timeout=120000)
        page.wait_for_function("document.querySelector('#chargement').hidden===true", timeout=60000)
        page.wait_for_timeout(1000)
        page.screenshot(path=os.path.join(DOSSIER, "propre-" + suffixe + ".png"))
        # Panneau de réglages ouvert (comparable à etat_1.png de l'original)
        if suffixe == "1440":
            page.locator("#bouton-reglages").click()
            page.wait_for_timeout(250)
            page.screenshot(path=os.path.join(DOSSIER, "propre-reglages.png"))
        # Contrôle de non-chevauchement des éléments fixes
        if suffixe == "390":
            mesures = page.evaluate("""() => {
                const r=s=>{const b=document.querySelector(s).getBoundingClientRect();return [Math.round(b.left),Math.round(b.top),Math.round(b.right),Math.round(b.bottom)];};
                return {titre:r('.top .titre'),actions:r('.top .actions'),frise:r('#frise'),copyright:r('#copyright'),globe:r('#globe')};
            }""")
            print("Mesures 390 px :", mesures, flush=True)
        ctx.close()
    nav.close()
print("Captures écrites dans", DOSSIER, flush=True)
