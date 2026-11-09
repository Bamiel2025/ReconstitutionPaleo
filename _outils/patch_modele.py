"""Applique au modèle les corrections « géolocalisation rigoureuse + fossiles ».

Chaque remplacement est asserté : si le modèle a changé, le script échoue
bruyamment au lieu de produire un HTML silencieusement incohérent.
"""
import os

ICI = os.path.dirname(os.path.abspath(__file__))
CHEMIN = os.path.join(ICI, "modele.html")
s = open(CHEMIN, encoding="utf-8").read()
modifications = 0


def remplace(ancien, nouveau, libelle):
    global s, modifications
    assert ancien in s, "motif introuvable : " + libelle
    assert s.count(ancien) == 1, "motif ambigu : " + libelle
    s = s.replace(ancien, nouveau, 1)
    modifications += 1


# ---------------------------------------------------------------- 1. marqueur
remplace(
    "/*__DONNEES__*/\n/*__CARTES__*/",
    "/*__DONNEES__*/\n/*__CARTES__*/\n/*__ENRICHISSEMENTS__*/",
    "marqueur enrichissements")

# ------------------------------------------------- 2. suppression du modèle simplifié
ancien_modele = s[s.index("/* ============================================================================\n   Repères de villes dans le passé"):s.index("/* ============================================================================\n   État et éléments d'interface")]
remplace(ancien_modele, r'''/* ============================================================================
   PALÉO-COORDONNÉES RÉELLES. PALEO[année][index de ville] = [lat, lng].
   Ces 119 × 56 valeurs proviennent du service /api/geo-reconstruct/<date> du site
   d'origine (modèle de plaques PALEOMAP), relevées puis intégrées hors ligne.
   null = la plaque de ce point ne remonte pas aussi loin : on n'invente rien,
   l'application l'affiche explicitement au lieu de placer un repère faux.
   ========================================================================== */
const Q_BORDS=10;                 /* frontières quantifiées au 1/10 de degré */
function positionReelle(ville,annee){
  const bloc=PALEO[String(annee)],i=VILLES.indexOf(ville);
  if(!bloc||i<0)return null;
  const p=bloc[String(i)];
  return (p&&typeof p[0]==='number'&&typeof p[1]==='number')?p:null;
}
function coordonneesTexte(p){
  const f=x=>Math.abs(x).toFixed(1).replace('.',',');
  return f(p[0])+'° '+(p[0]>=0?'N':'S')+', '+f(p[1])+'° '+(p[1]>=0?'E':'O');
}
function echapper(t){
  return String(t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
/* Contours et noms de pays RECONSTRUITS POUR CHAQUE DATE (assets de l'original),
   et non des frontières modernes. Lignes encodées en deltas : décodage paresseux. */
const CACHE_BORDS=new Map();
function bordsAnnee(y){
  if(CACHE_BORDS.has(y))return CACHE_BORDS.get(y);
  const d=FRONTIERES_PALEO[String(y)];
  if(!d){CACHE_BORDS.set(y,null);return null;}
  const lignes=[];
  for(const line of d.l){
    let la=0,lo=0;const pts=[];
    for(let i=0;i<line.length;i+=2){la+=line[i];lo+=line[i+1];pts.push([la/Q_BORDS,lo/Q_BORDS]);}
    if(pts.length>1)lignes.push(pts);
  }
  const noms=d.n.map(l=>[l[0],l[1]/Q_BORDS,l[2]/Q_BORDS]);
  const out={l:lignes,n:noms};
  CACHE_BORDS.set(y,out);
  return out;
}
/* Coordonnées ACTUELLES des sites de découverte : elles ne sont dessinées
   que sur la carte de 0 Ma. Les projeter dans le passé exigerait une
   reconstruction propre à chaque site, que nous n'avons pas. */
const CACHE_SITES=new Map();
function sitesDuTaxon(nom){
  if(CACHE_SITES.has(nom))return CACHE_SITES.get(nom);
  const out=[],vu=new Set();
  Object.keys(SITES_FOSSILES).forEach(v=>{
    ((SITES_FOSSILES[v]||{})[nom]||[]).forEach(c=>{
      const k=c[0].toFixed(2)+','+c[1].toFixed(2);
      if(!vu.has(k)){vu.add(k);out.push(c);}
    });
  });
  const pts=out.slice(0,80);
  CACHE_SITES.set(nom,pts);
  return pts;
}
function libelleVille(v){return (LIBELLES_VILLES[v[0]]||v[0]).split(',')[0];}
function libelleComplet(v){return LIBELLES_VILLES[v[0]]||v[0];}

''', "modèle de plaques simplifié -> données réelles")

# ---------------------------------------------------------------- 3. état
remplace(
    "let villeActive=null;\nlet chargementFait=false;",
    "let villeActive=null;\nlet taxonActif=null;\nlet chargementFait=false;",
    "état taxonActif")

# ---------------------------------------------------------- 4. bandeau ville + fossiles
debut = s.index("function majInfoVille(){")
fin = s.index("function majLecture(y,complet){")
remplace(s[debut:fin], r'''function majInfoVille(){
  const info=$('#info-ville');
  if(!villeActive){info.innerHTML='';return;}
  const pos=positionReelle(villeActive,mya);
  const quand=mya===0?'aujourd\'hui':'à '+mya+' Ma';
  let html='<b>'+echapper(libelleVille(villeActive))+'</b> — '+quand+' : ';
  if(pos){
    html+=coordonneesTexte(pos)+'.<br><span style="color:#9aa">Paléo-coordonnées du modèle de plaques du site d\'origine.</span>';
  }else{
    html+='<span style="color:#ff9a8a">position non reconstructible</span>.<br><span style="color:#9aa">La plaque de ce point ne remonte pas aussi loin : essaie une date plus récente.</span>';
  }
  const liste=FOSSILES_VILLES[villeActive[0]]||[];
  if(liste.length){
    html+='<div class="bloc-fossiles"><div class="titre-fossiles">Fossiles à proximité ('+liste.length+')</div><div class="chips-fossiles">';
    liste.forEach(n=>{html+='<button type="button" class="chip" data-taxon="'+echapper(n)+'">'+echapper(n)+'</button>';});
    html+='</div></div>';
  }
  info.innerHTML=html;
  info.querySelectorAll('[data-taxon]').forEach(b=>b.addEventListener('click',()=>ouvrirFiche(b.dataset.taxon)));
}
''', "majInfoVille + fossiles")

# --------------------------------------------------------------- 5. texte de lecture
remplace(
    r"""    if(villeActive&&y>0)txt+='<br><br><b>'+villeActive[0]+'</b> figure en <span style="color:#ff6b52">rouge</span> sur le globe (position estimée, modèle simplifié).';""",
    r"""    if(villeActive){
      const p=positionReelle(villeActive,y);
      txt+='<br><br><b>'+echapper(libelleVille(villeActive))+'</b> : '+(p
        ? 'repère <span style="color:#ff6b52">rouge</span> sur le globe, à '+coordonneesTexte(p)+' (modèle de plaques du site d\'origine).'
        : '<span style="color:#ff9a8a">position non reconstructible à cette date</span> : la plaque de ce point ne remonte pas aussi loin.');
    }""",
    "texte d'explication de la ville")

# ------------------------------------------------------ 6. frontières par année
debut = s.index("function dessinerFrontieres(){")
fin = s.index("function dessinerRepere(){")
remplace(s[debut:fin], r'''function dessinerFrontieres(){
  const b=bordsAnnee(mya);if(!b)return;
  ctx.strokeStyle='rgba(255,255,255,.45)';ctx.lineWidth=1;
  b.l.forEach(ring=>{
    ctx.beginPath();let ouvert=false,nb=0;
    for(let i=0;i<ring.length;i++){
      const p=projeter(ring[i][0],ring[i][1]);
      if(p[2]>0.04){if(!ouvert){ctx.moveTo(p[0],p[1]);ouvert=true;}else{ctx.lineTo(p[0],p[1]);nb++;}}
      else ouvert=false;
    }
    if(nb>1)ctx.stroke();
  });
}
function dessinerNoms(){
  const b=bordsAnnee(mya);if(!b)return;
  ctx.font='10px Helvetica,Arial,sans-serif';ctx.textAlign='center';ctx.textBaseline='middle';
  const occupe=[];let affiches=0;
  for(const e of b.n){
    if(affiches>=45)break;
    const q=projeter(e[1],e[2]);
    if(q[2]<.55)continue;
    const nom=e[0].length>18?e[0].slice(0,16)+'…':e[0];
    const larg=ctx.measureText(nom).width;
    if(occupe.some(o=>Math.abs(o[0]-q[0])<(o[2]+larg)/2+6&&Math.abs(o[1]-q[1])<11))continue;
    occupe.push([q[0],q[1],larg]);affiches++;
    ctx.fillStyle='rgba(0,0,0,.65)';ctx.fillText(nom,q[0]+1,q[1]+1);
    ctx.fillStyle='rgba(255,255,255,.9)';ctx.fillText(nom,q[0],q[1]);
  }
}
''', "frontières et noms par date")

# ------------------------------------------------------------------ 7. repère
remplace(
    "  const pos=positionPassee(villeActive,mya),q=projeter(pos[0],pos[1]);\n  if(q[2]<=0)return;",
    "  const pos=positionReelle(villeActive,mya);\n  if(!pos)return;\n  const q=projeter(pos[0],pos[1]);\n  if(q[2]<=0)return;",
    "repère réel / non reconstructible")

# --------------------------------------------- 8. sites de découverte + appel
remplace(
    "  if(options.noms)dessinerNoms();\n  dessinerRepere();\n}",
    r'''  if(options.noms)dessinerNoms();
  dessinerRepere();
  dessinerGisements();
}
function dessinerGisements(){
  if(!taxonActif||mya!==0)return;
  const pts=sitesDuTaxon(taxonActif);
  if(!pts.length)return;
  ctx.fillStyle='rgba(241,238,29,.9)';ctx.strokeStyle='rgba(0,0,0,.8)';ctx.lineWidth=1;
  pts.forEach(p=>{
    const q=projeter(p[0],p[1]);if(q[2]<=0.05)return;
    ctx.beginPath();ctx.arc(q[0],q[1],3.5,0,TAU);ctx.fill();ctx.stroke();
  });
}''',
    "sites de découverte")

# --------------------------------------------- 9. libellé du réglage frontières
remplace(
    "Frontières actuelles (repère) <input",
    "Frontières des pays (repositionnées) <input",
    "libellé réglage frontières")

# ------------------------------------------------------------ 10. HTML bandeau sites
remplace(
    '  <div class="info" id="info-ville"></div>\n</div>',
    r'''  <div class="info" id="info-ville"></div>
  <div id="sites-actifs" hidden></div>
</div>''',
    "bandeau sites actifs")

# --------------------------------------------------------- 11. modale fiche fossile
remplace(
    "<!-- Volet pédagogique -->",
    r'''<!-- Fiche d'un fossile -->
<div class="fenetre" id="fenetre-fossile">
  <div class="contenu" id="contenu-fossile">
    <button class="fermer" data-fermer aria-label="Fermer">&times;</button>
    <div id="corps-fossile"></div>
  </div>
</div>

<!-- Volet pédagogique -->''',
    "modale fiche fossile")

# --------------------------------------------------------------------- 12. CSS
remplace(
    "/* --- adaptation petits écrans --- */",
    r'''/* --- fossiles à proximité et fiches --- */
.bloc-fossiles{margin-top:10px;max-width:260px}
.titre-fossiles{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--jaune);margin-bottom:6px}
.chips-fossiles{display:flex;flex-wrap:wrap;gap:5px}
.chip{background:#202020;border:1px solid #666;color:#eee;border-radius:12px;padding:3px 9px;font-size:11px;cursor:pointer}
.chip:hover,.chip:focus-visible{background:var(--jaune);color:#000;border-color:var(--jaune)}
#corps-fossile h2{margin:0 0 14px}
.photo-fossile{margin:0 0 12px;text-align:center}
.photo-fossile img{max-width:100%;max-height:250px;border:1px solid #444;border-radius:5px;background:#fff}
.credit-photo{font-size:11px;color:#aaa;margin-top:4px}
.source-fiche{font-size:12px;color:#bbb}
.table-fiche{border-collapse:collapse;width:100%;margin:10px 0 14px;font-size:13px}
.table-fiche th,.table-fiche td{border-bottom:1px solid #333;padding:6px 8px;text-align:left;vertical-align:top}
.table-fiche th{color:var(--jaune);font-weight:600;width:38%}
.bouton-sites{background:#232323;border:1px solid var(--jaune);color:var(--jaune);border-radius:4px;padding:6px 11px;font-size:12px;cursor:pointer}
.bouton-sites:hover{background:var(--jaune);color:#000}
#sites-actifs{margin-top:8px;background:rgba(20,20,20,.88);border:1px solid var(--jaune);border-radius:5px;padding:6px 9px;font-size:11px;color:#eee;max-width:260px;line-height:1.5}
#sites-actifs[hidden]{display:none}
#sites-actifs button{background:none;border:0;color:var(--jaune);cursor:pointer;font-size:15px;float:right;line-height:1;padding:0 2px}

/* --- adaptation petits écrans --- */''',
    "CSS fossiles")

# ------------------------------------------------------------- 13. crédits : couleurs
remplace(
    "Les frontières et les noms de pays sont des <b>repères actuels</b> (Natural Earth 1:110m, domaine public), sans signification paléogéographique.",
    "Les frontières et les noms de pays, lorsqu'on les active, sont les contours des pays <b>actuels repositionnés à la date affichée</b> par le modèle de plaques : ils aident à suivre un territoire, mais ils n'ont aucune réalité politique ou géologique dans le passé.",
    "crédits : frontières")

# ------------------------------------------------------------- 14. crédits : limites
remplace(
    """    <h3>Limites de cette reconstitution</h3>
    <p>Les cartes et les textes sont issus des sources citées. En revanche, le <b>repère rouge d'une ville</b> dans le passé est calculé par un modèle de plaques <b>simplifié à visée pédagogique</b> : il donne une idée du déplacement des masses continentales, mais il ne coïncide pas exactement avec les cartes et ne doit pas servir à mesurer une paléolatitude. Seules les cartes ont une valeur de reconstitution publiée.</p>
    <p class="astuce">Étude de l'interface d'origine réalisée avec Craft Anything (captures 1440 / 900 / 390 px, jetons de design, relevé des 119 pas de temps). Cartes optimisées et intégrées en données locales.</p>""",
    r'''    <h3>Position des villes : données réelles, pas approximation</h3>
    <p>Le repère rouge d'une ville utilise les <b>paléo-coordonnées calculées par le service <code>/api/geo-reconstruct</code> du site d'origine</b> (modèle de plaques PALEOMAP). Elles ont été relevées pour les 56 villes proposées et les 119 dates, puis intégrées au fichier : l'application fonctionne sans réseau. Lorsque le modèle ne suit pas un point aussi loin dans le passé, l'application affiche « <b>position non reconstructible</b> » plutôt que de placer un repère inventé. L'alignement entre ces coordonnées, les contours de pays et la texture des cartes a été vérifié quantitativement.</p>
    <h3>Fossiles à proximité</h3>
    <p>Comme l'original, l'application propose, pour 41 villes sur 56, une liste de <b>fossiles signalés à proximité</b> (104 taxons au total). Chaque nom ouvre une fiche : période, régime alimentaire, région, gisements cités, extrait de Wikipédia en français lorsqu'il existe, illustration libre de <b>Wikimedia Commons</b> avec auteur et licence, et lien vers la page dédiée du site d'origine.</p>
    <p>Deux choix de rigueur : ces taxons ne sont <b>pas tous des dinosaures</b> (la liste contient aussi des reptiles marins comme <i>Pliosaurus</i> ou <i>Plesiosaurus</i>), d'où le terme général « fossiles ». Et les <b>illustrations du site d'origine ne sont pas reprises</b> : elles sont générées par IA et signalées par leur auteur comme « pouvant ne pas être scientifiquement exactes ». Les sites de découverte ne sont affichés sur le globe qu'à 0 Ma, car leurs coordonnées sont actuelles.</p>
    <h3>Limites</h3>
    <p>Cartes, paléo-coordonnées et contours repositionnés sont des <b>sorties de modèles</b>, cohérentes entre elles mais distinctes d'observations directes. Les cartes antérieures à 540 Ma restent beaucoup plus approximatives. Un point « non reconstructible » traduit une limite du modèle de plaques, pas une absence de terres à cette époque.</p>
    <p class="astuce">Étude de l'interface d'origine réalisée avec Craft Anything (captures 1440 / 900 / 390 px, jetons de design, relevé des 119 pas de temps). Cartes, paléo-coordonnées, contours par date, fiches et illustrations optimisés puis intégrés en données locales.</p>''',
    "crédits : limites et fossiles")

# ---------------------------------------------------------- 15. fiche professeur
remplace(
    """      <p>La frise couvre 1 milliard d'années avec des pas de 5 Ma : l'échelle est <b>linéaire en temps</b>, mais les périodes ont des durées très inégales. Les cartes antérieures à 540 Ma sont des approximations grossières (pas de données d'altitude). Les frontières et noms de pays proposés dans les réglages sont des repères <b>actuels</b> : les désactiver pendant l'activité. Le repère rouge des villes est un modèle simplifié, à ne pas utiliser pour mesurer une paléolatitude.</p>""",
    r'''      <p>La frise couvre 1 milliard d'années avec des pas de 5 Ma : l'échelle est <b>linéaire en temps</b>, mais les périodes ont des durées très inégales. Les cartes antérieures à 540 Ma sont des approximations grossières (pas de données d'altitude). Les frontières et noms de pays sont les contours actuels <b>repositionnés à la date affichée</b> : ce sont des repères commodes, sans signification politique passée ; les désactiver pendant l'activité.</p>
      <p>Le repère rouge des villes utilise les <b>vraies paléo-coordonnées</b> du modèle de plaques du site d'origine (et non une approximation) : il est cohérent avec les cartes, mais reste une sortie de modèle. Aux dates anciennes, certains points sont « non reconstructibles » : c'est l'occasion de discuter des limites d'un modèle scientifique et du refus de fabriquer une donnée manquante.</p>
      <p><b>Fossiles à proximité.</b> 41 villes sur 56 proposent 104 taxons fossiles. Les fiches donnent période, régime, région, gisements, un extrait Wikipédia FR et une illustration Wikimedia Commons créditée. Attention : tous ne sont pas des dinosaures (reptiles marins, etc.). Les sites de découverte ne sont affichés sur le globe qu'à 0 Ma, car leurs coordonnées sont actuelles.</p>''',
    "fiche prof : points de vigilance")
remplace(
    """      <p>Scotese &amp; Wright (2018), PALEOMAP PaleoDEM, CC BY 4.0 ; Kocsis &amp; Scotese (2021), CC BY 4.0 ; Merdith et al. (2021) pour les reconstructions antérieures à 540 Ma ; Natural Earth 1:110m (domaine public) pour les frontières actuelles. Visualisation d'origine : Ian Webster, dinosaurpictures.org.</p>""",
    """      <p>Scotese &amp; Wright (2018), PALEOMAP PaleoDEM, CC BY 4.0 ; Kocsis &amp; Scotese (2021), CC BY 4.0 ; Merdith et al. (2021) pour les reconstructions antérieures à 540 Ma. Paléo-coordonnées, contours par date et listes de fossiles : API et assets de dinosaurpictures.org (Ian Webster), intégrés hors ligne. Illustrations : Wikimedia Commons (auteur et licence dans chaque fiche) ; extraits : Wikipédia en français (CC BY-SA). Visualisation d'origine : Ian Webster.</p>""",
    "fiche prof : sources")

# -------------------------------------------------------------- 16. questions
remplace(
    r"""  ['6. Suivre un point au cours du temps', 'Cherche une ville dans le champ de recherche. Observe le repère rouge à 460 Ma, à 240 Ma et aujourd\'hui. Décris son déplacement, puis dis pourquoi ce repère ne peut pas servir à mesurer une paléolatitude.']""",
    r"""  ['6. Suivre un point au cours du temps', 'Cherche « Auriol » dans le champ de recherche. Relève sa position à 460 Ma, puis à 0 Ma (aujourd\'hui). Que constates-tu ? Essaie ensuite 1000 Ma : que répond l\'application et pourquoi ?'],
  ['7. Des fossiles près d\'une ville', 'Avec « Auriol » sélectionné, ouvre la liste « Fossiles à proximité ». Cite trois taxons proposés, puis ouvre la fiche de Hypselosaurus : à quelle période vivait-il, quel était son régime alimentaire et où ses fossiles ont-ils été trouvés ? Tous les taxons de la liste sont-ils des dinosaures ?']""",
    "questions 6 et 7")
remplace(
    r"""  'Le repère se déplace avec la plaque à laquelle la région est rattachée : il change nettement de latitude et de longitude entre 460 Ma, 240 Ma et aujourd\'hui. Mais il est calculé par un modèle de plaques simplifié, intégré à cette application pour l\'animation pédagogique : il ne coïncide pas avec les cartes paléogéographiques publiées et ne permet pas de mesurer une paléolatitude. Seules les cartes constituent un document scientifique exploitable.'""",
    r"""  'Aujourd\'hui Auriol est à 43,4° N / 5,6° E. À 460 Ma, le modèle de plaques du site d\'origine le place à 65,8° S / 92,2° E : la région qui deviendra la Provence appartenait alors au Gondwana, dans l\'hémisphère Sud. L\'écart illustre la dérive des continents sur 460 millions d\'années. À 1000 Ma, l\'application répond « position non reconstructible » : le modèle de plaques ne suit pas ce point aussi loin, et elle refuse de placer un repère inventé. C\'est une limite du modèle, pas une absence de terres à cette époque. Ces coordonnées sont des sorties de modèle cohérentes avec les cartes, pas des observations directes.',
  'Les cinq taxons proposés pour Auriol sont Hypselosaurus, Rhabdodon, Obelignathus, Ampelosaurus et Struthiosaurus. Hypselosaurus vivait au Crétacé, était herbivore et ses fossiles sont signalés en Europe, notamment en Aragon, à Barcelone et en Castille-La Manche (Espagne). Non : la liste « Fossiles à proximité » peut aussi contenir des reptiles marins (Pliosaurus, Plesiosaurus) qui ne sont PAS des dinosaures, d\'où le terme général « fossiles ». Les illustrations de l\'application proviennent de Wikimedia Commons avec auteur et licence, et non des images générées par IA du site d\'origine.'""",
    "corrigés 6 et 7")

# ------------------------------------------------------- 17. export : contexte ville
remplace(
    r"""  let t='LA TERRE ANCIENNE — fiche élève\nDate de travail : '+new Date().toLocaleDateString('fr-FR')+'\nDernière date observée : '+mya+' Ma ('+(EPOQUES[mya]?EPOQUES[mya].l:'')+')\n\n';""",
    r"""  let t='LA TERRE ANCIENNE — fiche élève\nDate de travail : '+new Date().toLocaleDateString('fr-FR')+'\nDernière date observée : '+mya+' Ma ('+(EPOQUES[mya]?EPOQUES[mya].l:'')+')\n';
  if(villeActive){
    const p=positionReelle(villeActive,mya);
    t+='Ville : '+libelleComplet(villeActive)+'\nPosition à '+mya+' Ma : '+(p?coordonneesTexte(p):'non reconstructible')+'\n';
    const f=FOSSILES_VILLES[villeActive[0]]||[];
    if(f.length)t+='Fossiles à proximité : '+f.join(', ')+'\n';
  }
  t+='\n';""",
    "export .txt : ville et fossiles")

# ------------------------------------------- 18. logique de la fiche fossile (JS)
remplace(
    "$('#bouton-credits').addEventListener('click',()=>{ouvrirFenetre('#fenetre-credits');});",
    r'''$('#bouton-credits').addEventListener('click',()=>{ouvrirFenetre('#fenetre-credits');});

/* --- Fiche d'un fossile signalé à proximité de la ville --- */
function afficherBandeauSites(){
  const b=$('#sites-actifs');
  if(!taxonActif){b.hidden=true;b.innerHTML='';return;}
  const n=sitesDuTaxon(taxonActif).length;
  b.hidden=false;
  b.innerHTML='<button type="button" id="masquer-sites" aria-label="Masquer les sites">&times;</button>'+
    '<b>'+echapper(taxonActif)+'</b> : '+n+' site(s) de découverte en <span style="color:var(--jaune)">jaune</span> sur la carte actuelle (0 Ma).';
  $('#masquer-sites').addEventListener('click',()=>{taxonActif=null;afficherBandeauSites();});
}
function ouvrirFiche(nom){
  const d=DINOS[nom];if(!d)return;
  const lieux=sitesDuTaxon(nom);
  let html='<h2>'+echapper(nom)+'</h2>';
  if(d.i){
    html+='<div class="photo-fossile"><img src="'+d.i+'" alt="Illustration de '+echapper(nom)+'">'+
          '<div class="credit-photo">'+echapper(d.c||'Wikimedia Commons')+' · Wikimedia Commons</div></div>';
  }
  html+='<p class="source-fiche">Fiche établie à partir de la <a href="'+echapper(d.u)+'" target="_blank" rel="noopener">page dédiée du site d\'origine</a>'+(d.t?' et de Wikipédia en français':'')+'.</p>';
  const faits=[];
  if(d.p)faits.push(['Période',d.p]);
  if(d.r)faits.push(['Régime alimentaire',d.r]);
  if(d.z)faits.push(['Région',d.z]);
  if(d.g)faits.push(['Gisements cités',d.g]);
  if(lieux.length)faits.push(['Sites répertoriés',String(lieux.length)]);
  if(faits.length){
    html+='<table class="table-fiche"><tbody>';
    faits.forEach(f=>{html+='<tr><th>'+echapper(f[0])+'</th><td>'+echapper(f[1])+'</td></tr>';});
    html+='</tbody></table>';
  }
  if(d.t)html+='<p>'+echapper(d.t)+'</p>';
  if(!d.i)html+='<p class="astuce">Aucune illustration libre vérifiée n\'a été trouvée pour ce taxon : la fiche s\'en tient aux données textuelles.</p>';
  html+='<p class="astuce">Les images du site d\'origine sont générées par IA et signalées comme « pouvant ne pas être scientifiquement exactes » : elles ne sont pas reprises ici. L\'illustration ci-dessus, lorsqu\'elle existe, vient de Wikimedia Commons avec son auteur et sa licence.</p>';
  if(lieux.length){
    html+='<p><button type="button" class="bouton-sites" id="voir-sites">Voir les sites de découverte sur le globe (0 Ma)</button></p>'+
          '<p class="astuce">Les coordonnées de ces sites sont actuelles : elles ne sont affichées que sur la carte d\'aujourd\'hui. Les replacer dans le passé demanderait une reconstruction propre à chaque site.</p>';
  }
  html+='<p><a href="'+echapper(d.u)+'" target="_blank" rel="noopener">Ouvrir la page dédiée sur dinosaurpictures.org ↗</a></p>';
  $('#corps-fossile').innerHTML=html;
  fermerFenetres();ouvrirFenetre('#fenetre-fossile');
  const voir=$('#voir-sites');
  if(voir)voir.addEventListener('click',()=>{
    taxonActif=nom;afficherBandeauSites();fermerFenetres();changerAnnee(0);
  });
}''',
    "logique fiche fossile")

# ------------------------------------------------- 19. en-tête commentaire du fichier
remplace(
    "  Frontières actuelles : Natural Earth 1:110m, domaine public.",
    "  Paléo-coordonnées des villes, contours de pays par date et fossiles à proximité :\n    API et assets de dinosaurpictures.org, intégrés hors ligne. Illustrations des fiches :\n    Wikimedia Commons (auteur et licence indiqués dans chaque fiche).",
    "en-tête crédits")

open(CHEMIN, "w", encoding="utf-8", newline="\n").write(s)
print("Remplacements appliqués :", modifications)
print("Taille modèle :", os.path.getsize(CHEMIN), "octets")
assert "positionPassee" not in s, "ancien modèle encore référencé"
assert "const PLAQUES=" not in s, "ancien modèle encore présent"
print("Ancien modèle simplifié : supprimé")
