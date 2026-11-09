
/*__DONNEES__*/
/*__CARTES__*/
/*__ENRICHISSEMENTS__*/

/* ============================================================================
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

/* ============================================================================
   État et éléments d'interface
   ========================================================================== */
const $=s=>document.querySelector(s);
const RAD2=Math.PI/180,TAU=Math.PI*2;
const MAX=STEPS[0];
let mya=460;
const h=parseInt((location.hash||'').slice(1),10);
if(STEPS.indexOf(h)>=0)mya=h;else if(!isNaN(h))mya=STEPS.reduce((a,b)=>Math.abs(b-h)<Math.abs(a-h)?b:a);
let villeActive=null;
let taxonActif=null;
let chargementFait=false;
const options={rotation:true,nuages:true,quadrillage:false,frontieres:false,noms:false,lumiere:false};

/* --- Sélecteur d'année de la barre supérieure --- */
const selAnnee=$('#annees');
STEPS.forEach(y=>{const o=document.createElement('option');o.value=y;o.textContent=y===0?'aujourd\'hui':'il y a '+y+' millions d\'années';selAnnee.appendChild(o);});
selAnnee.addEventListener('change',()=>changerAnnee(+selAnnee.value));

/* --- Menu « Aller à… » et repères de la frise --- */
const selAller=$('#aller-a');
const o0=document.createElement('option');o0.value='';o0.textContent='Aller à…';o0.selected=true;o0.disabled=true;selAller.appendChild(o0);
EVENEMENTS.forEach(e=>{const o=document.createElement('option');o.value=e.m;o.textContent=e.n+' ('+e.m+' Ma)';selAller.appendChild(o);});
selAller.addEventListener('change',()=>{changerAnnee(+selAller.value);selAller.selectedIndex=0;selAller.blur();});

const bandes=$('#bandes');
PERIODES.forEach(p=>{
  const d=document.createElement('div');
  d.className='bande'+(p.clair?' clair':'');
  d.style.left=(MAX-p.d)/MAX*100+'%';
  d.style.width=(p.d-p.f)/MAX*100+'%';
  d.style.backgroundColor=p.c;d.title=p.n+' : '+p.d+' à '+p.f+' Ma';
  d.__periode=p;bandes.appendChild(d);
});
function placerLibelles(){
  const largeur=bandes.clientWidth;
  [...bandes.children].forEach(d=>{
    const p=d.__periode,px=(p.d-p.f)/MAX*largeur;
    d.textContent=px>p.n.length*6.5+8?p.n:(px>p.a.length*7+4?p.a:'');
  });
}
const parDate={};
EVENEMENTS.forEach(e=>{if(!parDate[e.m])parDate[e.m]=[];parDate[e.m].push(e.n);});
const boiteRep=$('#reperes');
Object.keys(parDate).forEach(k=>{
  const m=+k,noms=parDate[k].join(', '),b=document.createElement('button');
  b.type='button';b.className='repere';b.style.left=(MAX-m)/MAX*100+'%';
  b.setAttribute('aria-label',noms+' ('+m+' millions d\'années)');b.setAttribute('data-tip',noms);
  b.addEventListener('click',e=>{e.stopPropagation();changerAnnee(m);});
  b.addEventListener('pointerdown',e=>e.stopPropagation());
  boiteRep.appendChild(b);
});

/* --- Lecture de la date --- */
function texteAnnee(y){return y===0?'Aujourd\'hui':y+' millions d\'années';}
function majInfoVille(){
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
function majLecture(y,complet){
  $('#combien').textContent=y===0?'':y;
  $('#unite').textContent=y===0?'Aujourd\'hui':"millions d'années";
  $('#sous-titre').textContent=y===0?'':(EPOQUES[y]?EPOQUES[y].l:'');
  $('#piste').setAttribute('aria-valuenow',y);
  $('#piste').setAttribute('aria-valuetext',texteAnnee(y));
  $('#curseur').style.left=(MAX-y)/MAX*100+'%';
  selAnnee.value=String(y);
  if(complet){
    const e=EPOQUES[y];
    let txt=e&&e.t?e.t:'';
    if(y===0)txt='Configuration actuelle des continents et des océans. Faites glisser la frise pour remonter le temps.';
    if(villeActive){
      const p=positionReelle(villeActive,y);
      txt+='<br><br><b>'+echapper(libelleVille(villeActive))+'</b> : '+(p
        ? 'repère <span style="color:#ff6b52">rouge</span> sur le globe, à '+coordonneesTexte(p)+' (modèle de plaques du site d\'origine).'
        : '<span style="color:#ff9a8a">position non reconstructible à cette date</span> : la plaque de ce point ne remonte pas aussi loin.');
    }
    $('#explication').innerHTML=txt;
    majInfoVille();
  }
}
function anneeLaPlusProche(y){return STEPS.reduce((a,b)=>Math.abs(b-y)<Math.abs(a-y)?b:a);}
function changerAnnee(y,remplaceHash){
  mya=anneeLaPlusProche(y);
  majLecture(mya,true);
  chargerCarte(mya);
  if(remplaceHash!==false){try{history.replaceState(null,'','#'+mya);}catch(e){}}
  try{localStorage.setItem('paleoTerre.date',String(mya));}catch(e){}
}

/* --- Frise : glisser, clavier --- */
const piste=$('#piste'),frise=$('#frise');
let glisse=false,dernierCommit=0;
function anneeDepuisX(clientX){
  const r=piste.getBoundingClientRect();
  return MAX*(1-Math.max(0,Math.min(1,(clientX-r.left)/r.width)));
}
piste.addEventListener('pointerdown',e=>{
  glisse=true;frise.classList.add('glisser');piste.setPointerCapture(e.pointerId);
  majLecture(anneeLaPlusProche(anneeDepuisX(e.clientX)),false);
});
piste.addEventListener('pointermove',e=>{
  if(!glisse)return;
  const y=anneeLaPlusProche(anneeDepuisX(e.clientX));
  majLecture(y,false);
  const t=performance.now();
  if(t-dernierCommit>140){dernierCommit=t;chargerCarte(y);}
});
function finGlisser(){if(!glisse)return;glisse=false;frise.classList.remove('glisser');changerAnnee(anneeLaPlusProche(anneeDepuisX(dernierX)),true);}
let dernierX=0;
document.addEventListener('pointermove',e=>{if(glisse)dernierX=e.clientX;},true);
piste.addEventListener('pointerup',e=>{dernierX=e.clientX;finGlisser();});
piste.addEventListener('pointercancel',()=>{glisse=false;frise.classList.remove('glisser');});
function pas(n){const i=STEPS.indexOf(mya);changerAnnee(STEPS[Math.max(0,Math.min(STEPS.length-1,i+n))]);}
document.addEventListener('keydown',e=>{
  if(document.querySelector('.fenetre.ouverte'))return;
  const t=e.target&&e.target.tagName;
  if(t==='INPUT'||t==='SELECT'||t==='TEXTAREA')return;
  if(e.key==='ArrowLeft'||e.key==='ArrowDown'){e.preventDefault();pas(-1);}
  else if(e.key==='ArrowRight'||e.key==='ArrowUp'){e.preventDefault();pas(1);}
  else if(e.key==='PageDown'){e.preventDefault();pas(-10);}
  else if(e.key==='PageUp'){e.preventDefault();pas(10);}
  else if(e.key==='Home'){e.preventDefault();changerAnnee(MAX);}
  else if(e.key==='End'){e.preventDefault();changerAnnee(0);}
});

/* --- Réglages --- */
$('#bouton-reglages').addEventListener('click',()=>{
  const b=$('#bouton-reglages'),p=$('#panneau-reglages');
  const ouvert=p.hidden;p.hidden=!ouvert;b.setAttribute('aria-expanded',String(ouvert));
});
const correspondance={'opt-rotation':'rotation','opt-nuages':'nuages','opt-quadrillage':'quadrillage','opt-frontieres':'frontieres','opt-noms':'noms','opt-lumiere':'lumiere'};
Object.keys(correspondance).forEach(id=>{
  $('#'+id).addEventListener('change',e=>{
    options[correspondance[id]]=e.target.checked;
    try{localStorage.setItem('paleoTerre.options',JSON.stringify(options));}catch(err){}
  });
});
try{const o=JSON.parse(localStorage.getItem('paleoTerre.options')||'null');if(o)Object.assign(options,o);}catch(e){}
Object.keys(correspondance).forEach(id=>{$('#'+id).checked=!!options[correspondance[id]];});

/* --- Recherche d'une ville --- */
const saisie=$('#saisie-ville'),propositions=$('#propositions'),infoVille=$('#info-ville'),effacer=$('#effacer-ville');
function normaliser(s){return s.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').trim();}
function afficherPropositions(terme){
  const q=normaliser(terme);
  if(q.length<1){propositions.style.display='none';return;}
  const r=VILLES.filter(v=>normaliser(v[0]).indexOf(q)>=0).slice(0,8);
  propositions.innerHTML='';
  r.forEach(v=>{const d=document.createElement('div');d.textContent=v[0];d.addEventListener('mousedown',()=>choisirVille(v));propositions.appendChild(d);});
  propositions.style.display=r.length?'block':'none';
}
saisie.addEventListener('input',()=>afficherPropositions(saisie.value));
saisie.addEventListener('focus',()=>afficherPropositions(saisie.value));
saisie.addEventListener('blur',()=>setTimeout(()=>propositions.style.display='none',150));
saisie.addEventListener('keydown',e=>{
  if(e.key==='Enter'){const q=normaliser(saisie.value);const v=VILLES.find(x=>normaliser(x[0])===q)||VILLES.find(x=>normaliser(x[0]).indexOf(q)>=0);if(v)choisirVille(v);}
  if(e.key==='Escape'){propositions.style.display='none';saisie.blur();}
});
function choisirVille(v){
  villeActive=v;saisie.value=v[0];propositions.style.display='none';effacer.hidden=false;
  majLecture(mya,true);
  try{localStorage.setItem('paleoTerre.ville',v[0]);}catch(e){}
}
effacer.addEventListener('click',()=>{
  villeActive=null;saisie.value='';infoVille.innerHTML='';effacer.hidden=true;majLecture(mya,true);
  try{localStorage.removeItem('paleoTerre.ville');}catch(e){}
});
try{const nom=localStorage.getItem('paleoTerre.ville');if(nom){const v=VILLES.find(x=>x[0]===nom);if(v)choisirVille(v);}}catch(e){}

/* ============================================================================
   Rendu du globe : projection d'une carte équirectangulaire sur une sphère,
   en canvas 2D pur (aucune bibliothèque, aucun WebGL requis).
   ========================================================================== */
const cv=$('#globe'),ctx=cv.getContext('2d',{alpha:false});
const TW=1024,TH=512;
let W=0,H=0,cx=0,cy=0,R=0,zoom=1,echelleGlobe=1;
let yaw=-0.15,pitch=0.06; /* cadrage calé sur la capture originale à 460 Ma */
const DECAL_U=0.0;
let fond=null,sph=null,sphCtx=null,imgSph=null, liste=[],nxA=null,nyA=null,nzA=null;
let texture=null,nuages=null;
const cacheCartes=new Map();
let nuageCharge=false,premiereCarte=false;
let forceNuages=0.62;
let dernierTemps=0,decalNuages=0;

function decodeImage(src,avecAlpha){
  return new Promise((res,rej)=>{
    const im=new Image();
    im.onload=()=>{
      const c=document.createElement('canvas');c.width=TW;c.height=TH;
      const g=c.getContext('2d',{willReadFrequently:true});
      g.clearRect(0,0,TW,TH);g.drawImage(im,0,0,TW,TH);
      res(g.getImageData(0,0,TW,TH).data);
    };
    im.onerror=()=>rej(new Error('image illisible'));
    im.src=src;
  });
}
function chargerCarte(y){
  if(cacheCartes.has(y)){
    texture=cacheCartes.get(y);
    cacheCartes.delete(y);cacheCartes.set(y,texture);
    if(!premiereCarte){premiereCarte=true;verifierPret();}
    return;
  }
  decodeImage(CARTES[y]).then(d=>{
    texture=d;cacheCartes.set(y,d);
    while(cacheCartes.size>8)cacheCartes.delete(cacheCartes.keys().next().value);
    if(!premiereCarte){premiereCarte=true;verifierPret();}
  }).catch(()=>{});
}
function verifierPret(){if(premiereCarte&&nuageCharge){$('#chargement').hidden=true;chargementFait=true;}}
decodeImage(NUAGES,true).then(d=>{nuages=d;nuageCharge=true;verifierPret();}).catch(()=>{nuageCharge=true;verifierPret();});

function faireFond(){
  fond=document.createElement('canvas');fond.width=W;fond.height=H;
  const g=fond.getContext('2d');g.fillStyle='#000';g.fillRect(0,0,W,H);
  let s=20261108;
  const rnd=()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296;};
  const n=Math.round(W*H/1900);
  for(let i=0;i<n;i++){
    const x=rnd()*W,y=rnd()*H,r=rnd(),a=.18+r*.65;
    g.fillStyle='rgba(255,255,255,'+a.toFixed(2)+')';
    g.beginPath();g.arc(x,y,r<.93?.45:r<.99?.8:1.25,0,TAU);g.fill();
  }
}
function redimensionner(){
  W=window.innerWidth;H=window.innerHeight;
  cv.width=W;cv.height=H;cv.style.width=W+'px';cv.style.height=H+'px';
  cx=W/2;cy=H/2;
  R=Math.max(60,Math.min(H*.27,W*.38)*zoom);
  faireFond();
  /* La texture est calculée à résolution bornée puis agrandie : le coût par
     image reste constant même au zoom maximum (important sur un poste de classe). */
  const RR=Math.min(R,220);
  const D=Math.ceil(2*RR)+2,centre=D/2;
  echelleGlobe=2*R/D;
  sph=document.createElement('canvas');sph.width=D;sph.height=D;
  sphCtx=sph.getContext('2d');
  imgSph=sphCtx.createImageData(D,D);
  const tab=[],ax=[],ay=[],az=[];
  for(let j=0;j<D;j++)for(let i=0;i<D;i++){
    const px=(i-centre)/RR,py=(j-centre)/RR,q=1-px*px-py*py;
    if(q<=0)continue;
    tab.push((j*D+i)*4);ax.push(px);ay.push(-py);az.push(Math.sqrt(q));
  }
  liste=tab;nxA=Float32Array.from(ax);nyA=Float32Array.from(ay);nzA=Float32Array.from(az);
  placerLibelles();
}
window.addEventListener('resize',redimensionner);

/* Projection d'un point géographique (degrés) vers l'écran ; z>0 = face visible. */
function projeter(lat,lon){
  const la=lat*RAD2,lo=lon*RAD2,cla=Math.cos(la);
  const wx=Math.sin(lo)*cla,wy=Math.sin(la),wz=Math.cos(lo)*cla;
  const cY=Math.cos(yaw),sY=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);
  const ux=wx*cY+wz*sY,uz=-wx*sY+wz*cY;
  const vx=ux,vy=wy*cp-uz*sp,vz=wy*sp+uz*cp;
  return [cx+vx*R,cy-vy*R,vz];
}
function tracerCourbe(points,couleur,epaisseur){
  ctx.strokeStyle=couleur;ctx.lineWidth=epaisseur;ctx.beginPath();
  let ouvert=false;
  for(let i=0;i<points.length;i++){
    const p=projeter(points[i][0],points[i][1]);
    if(p[2]>0.02){if(!ouvert){ctx.moveTo(p[0],p[1]);ouvert=true;}else ctx.lineTo(p[0],p[1]);}
    else ouvert=false;
  }
  ctx.stroke();
}
function dessinerQuadrillage(){
  for(let lon=-180;lon<180;lon+=30){
    const pts=[];for(let lat=-90;lat<=90;lat+=3)pts.push([lat,lon]);
    tracerCourbe(pts,'rgba(255,255,255,.22)',1);
  }
  for(let lat=-60;lat<=60;lat+=30){
    const pts=[];for(let lon=-180;lon<=180;lon+=3)pts.push([lat,lon]);
    tracerCourbe(pts,lat===0?'rgba(255,255,255,.42)':'rgba(255,255,255,.22)',lat===0?1.3:1);
  }
}
function dessinerFrontieres(){
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
function dessinerRepere(){
  if(!villeActive)return;
  const pos=positionReelle(villeActive,mya);
  if(!pos)return;
  const q=projeter(pos[0],pos[1]);
  if(q[2]<=0)return;
  ctx.beginPath();ctx.arc(q[0],q[1],7,0,TAU);
  ctx.fillStyle='#ff4433';ctx.fill();ctx.lineWidth=2;ctx.strokeStyle='#fff';ctx.stroke();
  ctx.font='bold 12px Helvetica,Arial,sans-serif';ctx.textAlign='left';ctx.textBaseline='middle';
  const t=villeActive[0],l=ctx.measureText(t).width;
  ctx.fillStyle='rgba(0,0,0,.72)';ctx.fillRect(q[0]+10,q[1]-10,l+12,20);
  ctx.fillStyle='#fff';ctx.fillText(t,q[0]+16,q[1]);
}

function dessinerGlobe(dt){
  ctx.drawImage(fond,0,0);
  const halo=ctx.createRadialGradient(cx,cy,R*.86,cx,cy,R*1.22);
  halo.addColorStop(0,'rgba(70,130,210,0)');
  halo.addColorStop(.72,'rgba(70,130,210,.10)');
  halo.addColorStop(1,'rgba(70,130,210,0)');
  ctx.fillStyle=halo;ctx.beginPath();ctx.arc(cx,cy,R*1.22,0,TAU);ctx.fill();

  if(texture){
    const cp=Math.cos(pitch),sp=Math.sin(pitch),cY=Math.cos(yaw),sY=Math.sin(yaw);
    const amb=options.lumiere?.88:.46, Lx=-.42,Ly=.46,Lz=.78;
    const out=imgSph.data,T=texture,N=nuages;
    const cw=options.nuages&&N?1:0;
    const taille=liste.length;
    for(let k=0;k<taille;k++){
      const nx=nxA[k],ny=nyA[k],nz=nzA[k];
      const y1=ny*cp+nz*sp, z1=-ny*sp+nz*cp;
      const wx=nx*cY-z1*sY, wz=nx*sY+z1*cY;
      const lat=Math.asin(y1<-1?-1:y1>1?1:y1);
      let u=.5+Math.atan2(wx,wz)/TAU+DECAL_U;u-=Math.floor(u);
      let v=.5-lat/Math.PI;if(v<0)v=0;else if(v>=1)v=.99999;
      const ti=(((v*TH)|0)*TW+((u*TW)|0))*4;
      let r=T[ti],g=T[ti+1],b=T[ti+2];
      let lum=nx*Lx+ny*Ly+nz*Lz;if(lum<0)lum=0;
      const sh=amb+(1-amb)*lum;
      if(cw){
        let cu=u+decalNuages;cu-=Math.floor(cu);
        const ci=(((v*TH)|0)*TW+((cu*TW)|0))*4;
        const a=Math.min(1,N[ci+3]/255*forceNuages);
        if(a>0){r=r*(1-a)+247*a;g=g*(1-a)+250*a;b=b*(1-a)+255*a;}
      }
      const bord=1-nz;
      const haloB=bord*bord*bord*34;
      const o=liste[k];
      out[o]=r*sh+haloB*.35;
      out[o+1]=g*sh+haloB*.65;
      out[o+2]=b*sh+haloB;
      out[o+3]=255;
    }
    sphCtx.putImageData(imgSph,0,0);
    const c=sph.width/2,lar=sph.width*echelleGlobe;
    ctx.drawImage(sph,cx-c*echelleGlobe,cy-c*echelleGlobe,lar,lar);
    ctx.beginPath();ctx.arc(cx,cy,R,0,TAU);
    ctx.strokeStyle='rgba(150,200,255,.22)';ctx.lineWidth=1.4;ctx.stroke();
  }
  if(options.quadrillage)dessinerQuadrillage();
  if(options.frontieres)dessinerFrontieres();
  if(options.noms)dessinerNoms();
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
}

function boucle(t){
  const dt=Math.min(60,t-dernierTemps||16);dernierTemps=t;
  if(options.rotation&&!dragging)yaw+=.00006*dt;
  decalNuages=(decalNuages+.000004*dt)%1;
  dessinerGlobe(dt);
  requestAnimationFrame(boucle);
}

/* --- Interaction avec le globe --- */
let dragging=false,px0=0,py0=0;
cv.addEventListener('pointerdown',e=>{dragging=true;px0=e.clientX;py0=e.clientY;cv.classList.add('dragging');cv.setPointerCapture(e.pointerId);});
cv.addEventListener('pointermove',e=>{
  if(!dragging)return;
  yaw+=(e.clientX-px0)*.006;
  pitch=Math.max(-1.25,Math.min(1.25,pitch+(e.clientY-py0)*.006));
  px0=e.clientX;py0=e.clientY;
});
function stopDrag(){dragging=false;cv.classList.remove('dragging');}
cv.addEventListener('pointerup',stopDrag);
cv.addEventListener('pointercancel',stopDrag);
cv.addEventListener('wheel',e=>{
  e.preventDefault();
  zoom=Math.max(.55,Math.min(2.4,zoom*(e.deltaY<0?1.09:.92)));
  redimensionner();
},{passive:false});

/* ============================================================================
   Fenêtres, activité pédagogique, bilan verrouillé
   ========================================================================== */
function ouvrirFenetre(id){$(id).classList.add('ouverte');}
function fermerFenetres(){document.querySelectorAll('.fenetre').forEach(f=>f.classList.remove('ouverte'));}
document.querySelectorAll('[data-fermer]').forEach(b=>b.addEventListener('click',fermerFenetres));
document.querySelectorAll('.fenetre').forEach(f=>f.addEventListener('click',e=>{if(e.target===f)fermerFenetres();}));
document.addEventListener('keydown',e=>{if(e.key==='Escape')fermerFenetres();});
$('#bouton-credits').addEventListener('click',()=>{ouvrirFenetre('#fenetre-credits');});

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
}
$('#lien-credits').addEventListener('click',e=>{e.preventDefault();ouvrirFenetre('#fenetre-credits');});

const QUESTIONS=[
  ['1. Observer une carte ancienne (460 Ma)', 'Place la frise sur 460 millions d\'années. Décris la disposition des terres et des mers, puis relève le nom de la période et les êtres vivants cités dans le texte.'],
  ['2. Une crise majeure (250 Ma)', 'Va à 250 Ma à l\'aide du menu « Aller à… ». Quel événement est signalé ? Que dit le texte sur les conséquences de cette crise ?'],
  ['3. Le supercontinent Pangée (240 Ma)', 'Compare la carte à 240 Ma et celle d\'aujourd\'hui. Cite deux différences nettes dans la répartition des continents.'],
  ['4. Lire une échelle de temps', 'À l\'aide de la frise, relève les dates d\'apparition des premières plantes terrestres et des premiers dinosaures. Calcule l\'écart de temps entre ces deux événements.'],
  ['5. Fiabilité des documents', 'Les cartes de 750 Ma et de 460 Ma ne reposent pas sur les mêmes données. Explique pourquoi celles de 750 Ma sont moins précises.'],
  ['6. Suivre un point au cours du temps', 'Cherche « Auriol » dans le champ de recherche. Relève sa position à 460 Ma, puis à 0 Ma (aujourd\'hui). Que constates-tu ? Essaie ensuite 1000 Ma : que répond l\'application et pourquoi ?'],
  ['7. Des fossiles près d\'une ville', 'Avec « Auriol » sélectionné, ouvre la liste « Fossiles à proximité ». Cite trois taxons proposés, puis ouvre la fiche de Hypselosaurus : à quelle période vivait-il, quel était son régime alimentaire et où ses fossiles ont-ils été trouvés ? Tous les taxons de la liste sont-ils des dinosaures ?']
];
const CORRIGES=[
  'À 460 Ma (Ordovicien moyen), les terres forment plusieurs masses continentales dispersées, surtout dans l\'hémisphère Sud (Gondwana), et de vastes mers peu profondes recouvrent une partie des continents. Le texte cite la Grande Biodiversification ordovicienne : trilobites, brachiopodes, nautiloïdes, poissons primitifs, premiers récifs coralliens et premières plantes simples sur les rivages humides. Aucune vie complexe sur terre.',
  '250 Ma : la « Grande Extinction », ou extinction de la fin du Permien — la plus grande crise de l\'histoire, probablement liée au volcanisme sibérien. Environ 90 % des espèces marines et la plupart des animaux terrestres disparaissent ; les récifs et les écosystèmes mettront plusieurs millions d\'années à se reconstituer.',
  'À 240 Ma, les masses continentales sont soudées en un seul supercontinent, la Pangée, entouré d\'un océan unique (Panthalassa) ; l\'intérieur est aride. Aujourd\'hui les continents sont dispersés, avec un Atlantique ouvert entre les Amériques et l\'Europe/Afrique, un océan Indien, et l\'Antarctique isolé au pôle Sud. On peut aussi citer l\'Inde qui a rejoint l\'Asie.',
  'Premières plantes terrestres : 430 Ma ; premiers dinosaures : 220 Ma. Écart : 430 − 220 = 210 millions d\'années. (Selon les repères retenus dans la frise : « premières plantes terrestres » à 430 Ma et « premiers dinosaures » à 220 Ma.)',
  'De 0 à 540 Ma, les cartes sont calculées à partir de modèles numériques de terrain paléo publiés (Scotese & Wright, 2018) et de paléo-côtes calibrées sur les fossiles. Avant 540 Ma (donc à 750 Ma), il n\'existe pas de données d\'altitude : les reliefs, la profondeur des océans et le tracé des côtes sont estimés à partir d\'un modèle cinématique de plaques (Merdith et al., 2021). Ce sont des approximations beaucoup plus grossières.',
  'Aujourd\'hui Auriol est à 43,4° N / 5,6° E. À 460 Ma, le modèle de plaques du site d\'origine le place à 65,8° S / 92,2° E : la région qui deviendra la Provence appartenait alors au Gondwana, dans l\'hémisphère Sud. L\'écart illustre la dérive des continents sur 460 millions d\'années. À 1000 Ma, l\'application répond « position non reconstructible » : le modèle de plaques ne suit pas ce point aussi loin, et elle refuse de placer un repère inventé. C\'est une limite du modèle, pas une absence de terres à cette époque. Ces coordonnées sont des sorties de modèle cohérentes avec les cartes, pas des observations directes.',
  'Les cinq taxons proposés pour Auriol sont Hypselosaurus, Rhabdodon, Obelignathus, Ampelosaurus et Struthiosaurus. Hypselosaurus vivait au Crétacé, était herbivore et ses fossiles sont signalés en Europe, notamment en Aragon, à Barcelone et en Castille-La Manche (Espagne). Non : la liste « Fossiles à proximité » peut aussi contenir des reptiles marins (Pliosaurus, Plesiosaurus) qui ne sont PAS des dinosaures, d\'où le terme général « fossiles ». Les illustrations de l\'application proviennent de Wikimedia Commons avec auteur et licence, et non des images générées par IA du site d\'origine.'
];
const CLE_REPONSES='paleoTerre.reponses.v1';
const boiteQ=$('#liste-questions'),boiteC=$('#liste-corriges');
QUESTIONS.forEach((q,i)=>{
  const d=document.createElement('div');d.className='question';
  d.innerHTML='<p><b>'+q[0]+'</b><br>'+q[1]+'</p><textarea data-q="'+i+'" placeholder="Ma réponse…"></textarea>';
  boiteQ.appendChild(d);
  const c=document.createElement('div');c.className='correction';
  c.innerHTML='<b>'+q[0]+'</b><br>'+CORRIGES[i];boiteC.appendChild(c);
});
const copie=$('#copie-questions');
QUESTIONS.forEach(q=>{
  const d=document.createElement('div');d.className='question';
  d.innerHTML='<p><b>'+q[0]+'</b><br>'+q[1]+'</p><div class="lignes"></div><div class="lignes"></div><div class="lignes"></div>';
  copie.appendChild(d);
});
const zones=[...document.querySelectorAll('textarea[data-q]')];
try{const r=JSON.parse(localStorage.getItem(CLE_REPONSES)||'[]');zones.forEach((z,i)=>z.value=r[i]||'');}catch(e){}
function sauverReponses(){try{localStorage.setItem(CLE_REPONSES,JSON.stringify(zones.map(z=>z.value)));}catch(e){}}
zones.forEach(z=>z.addEventListener('input',sauverReponses));
$('#effacer-reponses').addEventListener('click',()=>{if(confirm('Effacer toutes les réponses enregistrées ?')){zones.forEach(z=>z.value='');sauverReponses();}});
$('#imprimer').addEventListener('click',()=>window.print());
$('#exporter').addEventListener('click',()=>{
  let t='LA TERRE ANCIENNE — fiche élève\nDate de travail : '+new Date().toLocaleDateString('fr-FR')+'\nDernière date observée : '+mya+' Ma ('+(EPOQUES[mya]?EPOQUES[mya].l:'')+')\n';
  if(villeActive){
    const p=positionReelle(villeActive,mya);
    t+='Ville : '+libelleComplet(villeActive)+'\nPosition à '+mya+' Ma : '+(p?coordonneesTexte(p):'non reconstructible')+'\n';
    const f=FOSSILES_VILLES[villeActive[0]]||[];
    if(f.length)t+='Fossiles à proximité : '+f.join(', ')+'\n';
  }
  t+='\n';
  QUESTIONS.forEach((q,i)=>{t+=q[0]+'\n'+q[1]+'\nRéponse : '+(zones[i].value||'(non renseigné)')+'\n\n';});
  const b=new Blob([t],{type:'text/plain;charset=utf-8'}),a=document.createElement('a');
  a.href=URL.createObjectURL(b);a.download='Terre_ancienne_fiche_eleve.txt';a.click();
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
});

function activerVolet(nom){
  document.querySelectorAll('#fenetre-classe .onglets button').forEach(b=>b.classList.toggle('actif',b.dataset.volet===nom));
  document.querySelectorAll('#fenetre-classe .volet').forEach(v=>v.classList.toggle('actif',v.id==='volet-'+nom));
}
document.querySelectorAll('#fenetre-classe .onglets button').forEach(b=>b.addEventListener('click',()=>activerVolet(b.dataset.volet)));
[['#bouton-activite','activite'],['#bouton-bilan','bilan'],['#bouton-prof','prof']].forEach(([sel,nom])=>{
  $(sel).addEventListener('click',()=>{ouvrirFenetre('#fenetre-classe');activerVolet(nom);});
});
let deverrouille=false;
function tenterCode(){
  if($('#code-prof').value.trim()==='2027'){
    deverrouille=true;$('#contenu-classe').dataset.deverrouille='1';
    $('#message-code').textContent='Corrigé déverrouillé.';$('#message-code').style.color='#9fd47f';
  }else{
    $('#message-code').textContent='Code incorrect.';$('#message-code').style.color='#ff9a8a';
  }
}
$('#valider-code').addEventListener('click',tenterCode);
$('#code-prof').addEventListener('keydown',e=>{if(e.key==='Enter')tenterCode();});
['#bouton-bilan','#bouton-prof'].forEach(sel=>$(sel).addEventListener('click',()=>{
  if(!deverrouille)setTimeout(()=>$('#code-prof').focus(),80);
}));

/* --- Démarrage --- */
redimensionner();
try{const d=parseInt(localStorage.getItem('paleoTerre.date'),10);if(STEPS.indexOf(d)>=0&&STEPS.indexOf(h)<0)mya=d;}catch(e){}
majLecture(mya,true);
chargerCarte(mya);
requestAnimationFrame(boucle);
