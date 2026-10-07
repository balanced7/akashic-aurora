import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { SMAAPass } from 'three/addons/postprocessing/SMAAPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ROOTS, QUALITIES, buildChord } from './piano/chord-tree-model.mjs';
import { frameStats } from './piano/crystal-performance.mjs';

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const fail = error => { $('error').hidden = false; $('error').textContent = String(error?.message || error); $('loading').hidden = true; console.error(error); };
addEventListener('error', e => fail(e.error || e.message));
addEventListener('unhandledrejection', e => fail(e.reason));
const vec = (x=0,y=0,z=0) => new THREE.Vector3(x,y,z);
const up = vec(0,1,0);
const clamp = THREE.MathUtils.clamp;
let chord = buildChord({ root: Number(params.get('root') ?? 0), quality: params.get('quality') || 'major', seventh: params.get('seventh') || 'major',
  extensions: params.has('ext') ? params.get('ext').split(',').map(Number) : [9], sharp11: params.get('sharp11') === '1' });
let selected = null, transitionStart = -10000, morph = 1, last = performance.now(), lastStatus = 0;
let width = 1, height = 1, cssWidth = 1, cssHeight = 1, report = null;
let sample = null, intervals = [], orbiting = !reduced.matches;
let renderPaused = false, pausedAt = 0, pausedDuration = 0, frameId = 0, renderedFrames = 0;
const canvas = $('stage'), container = $('scene-frame');
const renderer = new THREE.WebGLRenderer({ canvas, antialias:false, powerPreference:'high-performance' });
renderer.setPixelRatio(1);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.08;
renderer.info.autoReset = false;
const scene = new THREE.Scene(); scene.background = new THREE.Color(0x070b10);
scene.fog = new THREE.FogExp2(0x070b10,.010);
const camera = new THREE.PerspectiveCamera(37,1,.1,180);
const controls = new OrbitControls(camera,canvas);
controls.target.set(0,8.8,0); controls.enableDamping = true; controls.dampingFactor=.065;
controls.minDistance=18; controls.maxDistance=85; controls.minPolarAngle=.2; controls.maxPolarAngle=Math.PI*.49;
controls.autoRotateSpeed=.34; controls.enablePan=false;
function home() { camera.position.set(23,16.5,34); controls.target.set(0,8.8,0); controls.update(); }
home();
const world = new THREE.Group(); scene.add(world);
scene.add(new THREE.HemisphereLight(0xe7ebff,0x090e1a,1.5));
const light = new THREE.DirectionalLight(0xffffff,3); light.position.set(-12,28,13); scene.add(light);
const rim = new THREE.DirectionalLight(0xb4cbec,3.3); rim.position.set(9,16,-16); scene.add(rim);
const fill = new THREE.DirectionalLight(0xffcfa6,1.3); fill.position.set(-15,4,-3); scene.add(fill);
const studio = new THREE.Scene(); const boxes=[];
for (const [x,y,z,w,h,intensity] of [[0,24,2,18,10,4],[-18,10,-3,8,18,3],[20,8,0,8,18,2]]) {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w,h),new THREE.MeshBasicMaterial({color:new THREE.Color(1,1,1).multiplyScalar(intensity),side:THREE.DoubleSide}));
  mesh.position.set(x,y,z); mesh.lookAt(0,8,0); studio.add(mesh); boxes.push(mesh);
}
const pmrem = new THREE.PMREMGenerator(renderer), env = pmrem.fromScene(studio,.08);
scene.environment = env.texture; pmrem.dispose(); boxes.forEach(m=>{m.geometry.dispose();m.material.dispose();});
const floor = new THREE.Mesh(new THREE.PlaneGeometry(180,180),new THREE.MeshStandardMaterial({color:0x0c121a,metalness:.45,roughness:.4,envMapIntensity:.2}));
floor.rotation.x=-Math.PI/2; floor.position.y=-.17; scene.add(floor);
const base = new THREE.Mesh(new THREE.CylinderGeometry(4.6,4.8,.26,128),new THREE.MeshPhysicalMaterial({color:0x111a22,metalness:.7,roughness:.3,clearcoat:1}));
base.position.y=-.05; world.add(base);
const target = new THREE.WebGLRenderTarget(1,1,{type:THREE.HalfFloatType,samples:4});
const composer = new EffectComposer(renderer,target);
composer.addPass(new RenderPass(scene,camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(1,1),.35,.5,.95);
composer.addPass(bloom);
const smaa = new SMAAPass(); composer.addPass(smaa); composer.addPass(new OutputPass());
const colorFor = (shade, output = new THREE.Color()) => output.setHSL(chord.root.hue/360, .69-(shade-.25)*.36, shade);
const trunkAt = y => vec(Math.sin(y*.34)*.22, y, Math.sin(y*.26)*.3);
const branchMaterials=[], records=[];
const dummy = new THREE.Object3D();
const wind = {value:0};
function material(shade, morphUniform) {
  const mat = new THREE.MeshPhysicalMaterial({color:colorFor(shade),emissive:colorFor(shade),emissiveIntensity:.18,metalness:.52,roughness:.29,clearcoat:1,clearcoatRoughness:.15,envMapIntensity:.75});
  mat.userData.shade=shade;
  if (morphUniform) {
    mat.onBeforeCompile = shader => {
      shader.uniforms.uShape=morphUniform;
      shader.vertexShader = 'uniform float uShape; attribute vec3 goalPosition; attribute vec3 goalNormal;\n' + shader.vertexShader;
      shader.vertexShader = shader.vertexShader.replace('#include <beginnormal_vertex>', 'vec3 objectNormal = normalize(mix(normal, goalNormal, uShape));');
      shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', 'vec3 transformed = mix(position, goalPosition, uShape);');
    };
    mat.customProgramCacheKey = () => 'arbor-branch-morph-v1';
  }
  branchMaterials.push(mat); return mat;
}

// Tapered tubes share a fixed topology. Only ordinary goal attributes change.
function tubeData(curve,radius,segments=40,sides=9) {
  const frames=curve.computeFrenetFrames(segments,false),positions=[],normals=[],indices=[];
  for(let i=0;i<=segments;i++) {
    const t=i/segments, p=curve.getPoint(t), r=radius*(.035+.965*Math.pow(1-t,.84));
    for(let j=0;j<=sides;j++) {
      const a=j/sides*Math.PI*2, n=frames.normals[i].clone().multiplyScalar(Math.cos(a)).addScaledVector(frames.binormals[i],Math.sin(a));
      positions.push(p.x+n.x*r,p.y+n.y*r,p.z+n.z*r); normals.push(n.x,n.y,n.z);
      if(i<segments && j<sides) { const k=i*(sides+1)+j; indices.push(k,k+sides+1,k+1,k+1,k+sides+1,k+sides+2); }
    }
  }
  return {positions,normals,indices};
}
function combine(tubes) {
  const positions=[],normals=[],indices=[];
  for(const tube of tubes) {const offset=positions.length/3; positions.push(...tube.positions);normals.push(...tube.normals);indices.push(...tube.indices.map(i=>i+offset));}
  return {positions:new Float32Array(positions),normals:new Float32Array(normals),indices};
}
function geometry(data) {
  const geo=new THREE.BufferGeometry();geo.setIndex(data.indices);
  geo.setAttribute('position',new THREE.BufferAttribute(data.positions.slice(),3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('normal',new THREE.BufferAttribute(data.normals.slice(),3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('goalPosition',new THREE.BufferAttribute(data.positions.slice(),3).setUsage(THREE.DynamicDrawUsage));
  geo.setAttribute('goalNormal',new THREE.BufferAttribute(data.normals.slice(),3).setUsage(THREE.DynamicDrawUsage));
  return geo;
}
const attachments=[0,3.8,5.1,7.1,9,11,13];
const tips=[null,[-6.2,7.4,2.5],[6.6,8.9,1.5],[-5.4,11.9,-2.4],[5.1,14.2,-2.1],[-3.6,16.1,1.9],[1.6,18.5,.1]];
function branchShape(slot,active) {
  const {spread,curl}=chord.family;
  const start=trunkAt(attachments[slot]);
  const [x,y,z]=tips[slot];
  const end=vec(x*(slot<3?spread:1),y+(slot===1?-curl*.7:slot===2?curl*.15:0),z+(slot<3?curl*.6:0));
  if(slot===3) end.y+=chord.state.seventh==='major'?.45:chord.state.seventh==='dim'?-.5:0;
  if(slot===5 && chord.state.sharp11) {end.y+=.65;end.z+=.8;}
  const sign=Math.sign(x), ctrl1=start.clone().add(vec(sign*.7,1.3,-.2));
  const ctrl2=end.clone().add(vec(-sign*2.4,-1.15-curl*.35,-1.1));
  const curve=new THREE.CubicBezierCurve3(start,ctrl1,ctrl2,end);
  const main=tubeData(curve,.22-(slot-1)*.022,48,10), tubes=[main], leaves=[];
  for(let j=0;j<12;j++) {
    const t=.34+j*.049, origin=curve.getPoint(t), tangent=curve.getTangent(t);
    const angle=j*2.399+slot*.75;
    const outward=vec(Math.cos(angle),.35,Math.sin(angle)).normalize();
    const length=(1.35+Math.sin(j*.28)*.45)*(slot<3?spread:1);
    const tip=origin.clone().addScaledVector(outward,length).addScaledVector(tangent,.75).add(vec(0,.3,0));
    const twig=new THREE.CubicBezierCurve3(origin,origin.clone().addScaledVector(tangent,.55),tip.clone().add(vec(0,-.45,0)),tip);
    tubes.push(tubeData(twig,.037,12,6));
    for(let k=0;k<6;k++) {
      const u=.35+k*.115, p=twig.getPoint(u), dir=twig.getTangent(u);
      const side=k%2?1:-1, leafDir=dir.clone().addScaledVector(vec(-outward.z,.45,outward.x),side*.7).normalize();
      const quaternion=new THREE.Quaternion().setFromUnitVectors(up,leafDir);
      const size=(.63+.3*Math.sin(k*1.71+j))*(slot<3?1:.87);
      leaves.push({position:p,quaternion,scale:vec(size*.95,size,size*.39)});
    }
  }
  // The two tip filaments become an unmistakable fork for either suspension.
  for(let k=0;k<2;k++) {
    const fork=slot===1 && chord.state.quality.startsWith('sus');
    const origin=curve.getPoint(.83), tip=end.clone().add(vec((k?1:-1)*(fork?.6:.015),fork?.45:.02,k?-.15:.15));
    tubes.push(tubeData(new THREE.CubicBezierCurve3(origin,end.clone().add(vec(0,.05,0)),tip.clone().add(vec(0,-.25,0)),tip),fork?.057:.002,16,7));
  }
  const data=combine(tubes);
  if(!active) {
    for(let i=0;i<data.positions.length;i+=3) {data.positions[i]=start.x+(data.positions[i]-start.x)*.0001; data.positions[i+1]=start.y+(data.positions[i+1]-start.y)*.0001;data.positions[i+2]=start.z+(data.positions[i+2]-start.z)*.0001;}
    leaves.forEach(l=>{l.position.copy(start);l.scale.multiplyScalar(.0001);});
    end.copy(start);
  }
  return {data,leaves,end,active};
}
function trunkData() {
  let top=5.7;for(let i=1;i<7;i++)if(chord.tones[i])top=attachments[i]+.9;
  const curve=new THREE.CatmullRomCurve3(Array.from({length:15},(_,i)=>trunkAt(top*i/14)));
  return combine([tubeData(curve,.42,80,14)]);
}
const trunkMorph={value:1}, trunkMaterial=material(.26,trunkMorph), trunk=new THREE.Mesh(geometry(trunkData()),trunkMaterial);
trunk.frustumCulled=false;world.add(trunk);
for(let i=0;i<9;i++) {
  const a=i/9*Math.PI*2, end=vec(Math.cos(a)*(2.8+i%3*.5),.12,Math.sin(a)*(2.8+i%3*.5));
  const curve=new THREE.CubicBezierCurve3(vec(0,.62,0),vec(Math.cos(a)*.4,.08,Math.sin(a)*.4),end.clone().multiplyScalar(.75).setY(.14),end);
  const data=tubeData(curve,.16,28,9), geo=new THREE.BufferGeometry();geo.setIndex(data.indices);geo.setAttribute('position',new THREE.Float32BufferAttribute(data.positions,3));geo.setAttribute('normal',new THREE.Float32BufferAttribute(data.normals,3));
  world.add(new THREE.Mesh(geo,material(.27)));
}
const ringMaterial=material(.42);
for(const radius of [4.42,4.6]) {const ring=new THREE.Mesh(new THREE.TorusGeometry(radius,.013,8,180),ringMaterial);ring.rotation.x=Math.PI/2;ring.position.y=.105;world.add(ring);}
const seed=new THREE.Mesh(new THREE.IcosahedronGeometry(.31,3),material(.65));seed.position.y=.6;world.add(seed);
const leafGeometry=new THREE.LatheGeometry([new THREE.Vector2(0,0),new THREE.Vector2(.12,.18),new THREE.Vector2(.20,.48),new THREE.Vector2(.14,.83),new THREE.Vector2(0,1.22)],8);
const budGeometry=new THREE.IcosahedronGeometry(.14,2);
const gemGeometry=new THREE.OctahedronGeometry(.38,0);
const haloGeometry=new THREE.TorusGeometry(.36,.034,8,48);
const helixCurve=new THREE.CatmullRomCurve3(Array.from({length:65},(_,i)=>{const a=i/64*Math.PI*4;return vec(Math.cos(a)*.23,i/64*.9,Math.sin(a)*.23);}));
const helixGeometry=new THREE.TubeGeometry(helixCurve,64,.025,7,false);
const labelElements=[];
const clonePose=p=>({position:p.position.clone(),quaternion:p.quaternion.clone(),scale:p.scale.clone()});
for(let slot=1;slot<7;slot++) {
  const shape=branchShape(slot,!!chord.tones[slot]), blend={value:1}, mat=material(.30+slot*.076,blend);
  const mesh=new THREE.Mesh(geometry(shape.data),mat);mesh.frustumCulled=false;world.add(mesh);
  const leafMat=material(.34+slot*.083);
  leafMat.metalness=.27;leafMat.roughness=.23;leafMat.emissiveIntensity=.09;
  leafMat.onBeforeCompile=shader=>{shader.uniforms.uWind=wind;shader.vertexShader='uniform float uWind;\n'+shader.vertexShader;shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',`#include <begin_vertex>\n transformed.x += sin(uWind+instanceMatrix[3].y*1.4+instanceMatrix[3].x)*.035*position.y*position.y;`);};
  leafMat.customProgramCacheKey=()=> 'arbor-leaf-wind-v1';
  const leaves=new THREE.InstancedMesh(leafGeometry,leafMat,shape.leaves.length);leaves.instanceMatrix.setUsage(THREE.DynamicDrawUsage);leaves.frustumCulled=false;world.add(leaves);
  const bud=new THREE.Mesh(budGeometry,material(.52+slot*.058));world.add(bud);
  const ornament=new THREE.Group();
  const gem=new THREE.Mesh(gemGeometry,mat),haloA=new THREE.Mesh(haloGeometry,mat),haloB=new THREE.Mesh(haloGeometry,mat),helix=new THREE.Mesh(helixGeometry,mat);
  // Ornament materials do not use branch-morph attributes.
  const ornamentMat=material(.5+slot*.045);[gem,haloA,haloB,helix].forEach(m=>{m.material=ornamentMat;ornament.add(m);});
  haloA.rotation.y=.7;haloB.rotation.y=-.7;haloA.position.x=-.17;haloB.position.x=.17;world.add(ornament);
  const label=document.createElement('button');label.className='tone-label';label.hidden=!shape.active;label.addEventListener('click',()=>selectTone(slot));$('labels').append(label);labelElements[slot]=label;
  const record={slot,mesh,blend,mat,leafMat,leaves,bud,ornament,gem,haloA,haloB,helix,shape,fromLeaves:shape.leaves.map(clonePose),toLeaves:shape.leaves,currentLeaves:shape.leaves.map(clonePose),fromEnd:shape.end.clone(),end:shape.end.clone(),toEnd:shape.end.clone(),active:shape.active,wasActive:shape.active};
  records.push(record);
}
const scratchColor=new THREE.Color();
function moveGeometry(mesh,data,amount) {
  for(const [base,goal,source] of [['position','goalPosition',data.positions],['normal','goalNormal',data.normals]]) {
    const a=mesh.geometry.getAttribute(base),b=mesh.geometry.getAttribute(goal);
    for(let i=0;i<a.array.length;i++)a.array[i]+=(b.array[i]-a.array[i])*amount;
    a.needsUpdate=true;b.array.set(source);b.needsUpdate=true;
  }
}
function setOrnaments(record) {
  const q=chord.state.quality;
  record.gem.visible=record.slot===2&&(q==='dim'||q==='aug');
  record.gem.scale.set(q==='aug'?.7:1,q==='aug'?2.6:1,q==='aug'?.7:1);
  record.haloA.visible=record.haloB.visible=record.slot===1&&q.startsWith('sus');
  record.helix.visible=record.slot===5&&chord.state.sharp11;
}
function setShape() {
  moveGeometry(trunk,trunkData(),morph);trunkMorph.value=0;
  records.forEach(r=>{
    const shape=branchShape(r.slot,!!chord.tones[r.slot]);
    moveGeometry(r.mesh,shape.data,morph);r.blend.value=0;
    r.fromLeaves=r.currentLeaves.map(clonePose);r.toLeaves=shape.leaves;
    r.fromEnd.copy(r.end);r.toEnd.copy(shape.end);r.wasActive=r.active;r.active=shape.active;r.shape=shape;
    setOrnaments(r);
  });
  transitionStart=renderPaused?pausedAt:performance.now();morph=0;
}
function updateLeaves(r,t) {
  r.currentLeaves.forEach((p,i)=>{
    const a=r.fromLeaves[i],b=r.toLeaves[i];p.position.lerpVectors(a.position,b.position,t);p.quaternion.slerpQuaternions(a.quaternion,b.quaternion,t);p.scale.lerpVectors(a.scale,b.scale,t);
    dummy.position.copy(p.position);dummy.quaternion.copy(p.quaternion);dummy.scale.copy(p.scale);dummy.updateMatrix();r.leaves.setMatrixAt(i,dummy.matrix);
  });r.leaves.instanceMatrix.needsUpdate=true;
}

function cancelMeasurement(reason) {
  if(sample){sample=null;$('measure').disabled=renderPaused;$('measurement').textContent=`Cancelled: ${reason}.`;}
  else if(report){$('measurement').textContent='Measure again after changes.';}
  report=null;delete $('measurement').dataset.report;
}
function setRenderPaused(value) {
  if(renderPaused===value)return;
  renderPaused=value;
  const now=performance.now();
  if(value) {
    pausedAt=now;cancelAnimationFrame(frameId);frameId=0;
    cancelMeasurement('render paused');
    $('render-status').textContent='Rendering paused';
  } else {
    const elapsed=now-pausedAt;transitionStart+=elapsed;pausedDuration+=elapsed;
    last=now;lastStatus=0;intervals=[];frameId=requestAnimationFrame(frame);
  }
  controls.enabled=!value;
  $('measure').disabled=value;
  $('pause-render').textContent=value?'Resume render':'Pause render';
  $('pause-render').setAttribute('aria-pressed',String(value));
  $('pause-notice').hidden=!value;
  $('render-status').dataset.frames=String(renderedFrames);
}
$('pause-render').addEventListener('click',()=>setRenderPaused(!renderPaused));
function selectTone(slot) {
  selected=selected===slot?null:slot;
  const tone=selected===null?null:chord.tones[selected];
  $('tone-detail').textContent=tone?`${tone.note} · ${tone.role}${tone.slot===1&&chord.state.quality.startsWith('sus')?' · replaces the third':''}`:'Select a tone to trace its branch.';
  document.querySelectorAll('[data-tone]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.tone)===selected)));
  records.forEach(r=>{labelElements[r.slot].setAttribute('aria-pressed',String(r.slot===selected));});
}
for(const root of ROOTS) {
  const b=document.createElement('button');b.textContent=root.name;b.dataset.root=root.pc;b.style.setProperty('--note-hue',root.hue);b.setAttribute('aria-label',`Root ${root.name}`);b.addEventListener('click',()=>apply({...chord.state,root:root.pc}));$('roots').append(b);
}
function paintUI() {
  document.documentElement.style.setProperty('--hue',chord.root.hue);
  $('root-name').textContent=chord.root.name;$('scene-root').textContent=chord.root.name;
  $('scene-quality').textContent=chord.family.name.toUpperCase();
  $('quality').value=chord.state.quality;$('seventh').value=chord.state.seventh;
  $('seventh').querySelector('[value="dim"]').disabled=chord.state.quality!=='dim';
  $('nine').checked=chord.state.extensions.includes(9);$('eleven').checked=chord.state.extensions.includes(11);$('thirteen').checked=chord.state.extensions.includes(13);
  $('nine').disabled=chord.state.quality==='sus2';$('eleven').disabled=chord.state.quality==='sus4'&&!chord.state.sharp11;
  $('thirteen').disabled=chord.state.seventh==='dim';$('sharp-eleven').checked=chord.state.sharp11;$('sharp-eleven').disabled=chord.state.quality==='dim';
  $('modifier').textContent=chord.modifier;
  $('chord-name').textContent=chord.name;$('chord-notes').textContent=chord.notes.join(' · ');
  document.querySelectorAll('[data-root]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.root)===chord.state.root)));
  $('tones').replaceChildren();
  chord.tones.forEach((tone,slot)=>{
    if(!tone)return;
    const b=document.createElement('button');b.dataset.tone=slot;b.textContent=`${tone.degree} · ${tone.note}`;b.style.setProperty('--tone-color',`hsl(${tone.hue} 65% ${tone.shade*100}%)`);b.setAttribute('aria-label',`${tone.note}, ${tone.role}`);b.setAttribute('aria-pressed','false');b.addEventListener('click',()=>selectTone(slot));$('tones').append(b);
    if(slot){labelElements[slot].innerHTML=`${tone.note}<span class="degree">${tone.degree}</span>`;labelElements[slot].setAttribute('aria-label',`${tone.note}, ${tone.role}`);labelElements[slot].setAttribute('aria-pressed','false');}
  });
  selected=null;$('tone-detail').textContent='Select a tone to trace its branch.';
}
function apply(input) {
  cancelMeasurement('chord changed');chord=buildChord(input);paintUI();setShape();
  const url=new URL(location.href);url.searchParams.set('root',chord.state.root);url.searchParams.set('quality',chord.state.quality);url.searchParams.set('seventh',chord.state.seventh);url.searchParams.set('ext',chord.state.extensions.join(','));url.searchParams.set('sharp11',chord.state.sharp11?'1':'0');history.replaceState(null,'',url);
}
function readControls(event) {
  if(event?.target===$('eleven')&&!$('eleven').checked)$('sharp-eleven').checked=false;
  const sharp11=$('sharp-eleven').checked;
  apply({root:chord.state.root,quality:$('quality').value,seventh:$('seventh').value,extensions:[$('nine').checked?9:0,($('eleven').checked||sharp11)?11:0,$('thirteen').checked?13:0].filter(Boolean),sharp11});
}
for(const id of ['quality','seventh','nine','eleven','thirteen','sharp-eleven'])$(id).addEventListener('change',readControls);
function orbitState() {controls.autoRotate=orbiting;$('orbit').textContent=orbiting?'Pause orbit':'Slow orbit';$('orbit').setAttribute('aria-pressed',String(orbiting));}
$('orbit').addEventListener('click',()=>{cancelMeasurement('camera changed');orbiting=!orbiting;orbitState();});
controls.addEventListener('start',()=>{cancelMeasurement('camera moved');orbiting=false;orbitState();});
$('home').addEventListener('click',()=>{cancelMeasurement('camera reset');home();});
$('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){fail(e);}});
if(params.get('resolution')==='4k')$('resolution').value='4k';
function resize() {
  cancelMeasurement('size changed');const bounds=container.getBoundingClientRect();cssWidth=bounds.width;cssHeight=bounds.height;
  [width,height]=$('resolution').value==='4k'?[3840,2160]:[Math.max(1,Math.round(cssWidth*devicePixelRatio)),Math.max(1,Math.round(cssHeight*devicePixelRatio))];
  renderer.setSize(width,height,false);composer.setSize(width,height);camera.aspect=width/height;
  // Preserve enough horizontal field of view for the widest augmented crown.
  camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(37/2))*Math.max(1,.9/camera.aspect)));
  camera.updateProjectionMatrix();intervals=[];
}
new ResizeObserver(resize).observe(container);let dpr=devicePixelRatio;
setInterval(()=>{if(dpr!==devicePixelRatio){dpr=devicePixelRatio;resize();}},1000);
$('resolution').addEventListener('change',()=>{resize();const u=new URL(location.href);u.searchParams.set('resolution',$('resolution').value);history.replaceState(null,'',u);});
reduced.addEventListener('change',()=>{if(reduced.matches){orbiting=false;orbitState();}cancelMeasurement('motion preference changed');});
document.addEventListener('visibilitychange',()=>{cancelMeasurement('visibility changed');last=performance.now();intervals=[];});
$('measure').addEventListener('click',()=>{sample={start:performance.now()+2000,frames:[],cpu:[]};$('measure').disabled=true;$('measurement').textContent='Warming up…';});

const projected=vec();
function placeLabels() {
  const fit=Math.min(cssWidth/width,cssHeight/height),imageW=width*fit,imageH=height*fit,ox=(cssWidth-imageW)/2,oy=(cssHeight-imageH)/2;
  const occupied=[];
  const order=[...records].sort((a,b)=>(b.slot===selected?1:0)-(a.slot===selected?1:0)||camera.position.distanceToSquared(a.end)-camera.position.distanceToSquared(b.end));
  for(const r of order) {
    const label=labelElements[r.slot];
    if(!r.active||!$('show-labels').checked||morph<.85){label.hidden=true;continue;}
    projected.copy(r.end).project(camera);const x=ox+(projected.x+1)/2*imageW,y=oy+(1-projected.y)/2*imageH-19;
    const rect={x:x-31,y:y-11,w:62,h:23};
    if(projected.z>1||projected.z< -1||x<35||x>cssWidth-35||y<16||y>cssHeight-45||occupied.some(a=>Math.abs(a.x-rect.x)<65&&Math.abs(a.y-rect.y)<26)){label.hidden=true;continue;}
    occupied.push(rect);label.hidden=false;label.style.left=`${x}px`;label.style.top=`${y}px`;
  }
}
function frame(now) {
  frameId=0;
  if(renderPaused)return;
  frameId=requestAnimationFrame(frame);
  const delta=now-last;last=now;if(document.hidden)return;
  const cpuStart=performance.now();
  const dt=Math.min(delta/1000,.05), blend=reduced.matches?1:clamp((now-transitionStart)/1250,0,1), nextMorph=blend*blend*(3-2*blend);
  const changed=morph!==nextMorph;morph=nextMorph;trunkMorph.value=morph;
  branchMaterials.forEach(mat=>{colorFor(mat.userData.shade,scratchColor);mat.color.lerp(scratchColor,1-Math.exp(-dt*7));mat.emissive.copy(mat.color);});
  trunkMaterial.emissiveIntensity=selected===0?.65:.18;
  seed.material.emissiveIntensity=selected===0?1.2:.18;
  for(const r of records) {
    r.blend.value=morph;r.end.lerpVectors(r.fromEnd,r.toEnd,morph);
    if(changed)updateLeaves(r,morph);
    const visibility=r.active?1:r.wasActive?1-morph:0;
    r.mesh.visible=r.leaves.visible=visibility>.0001;
    const scale=r.active?(r.wasActive?1:morph):1-morph;r.bud.position.copy(r.end);r.bud.scale.setScalar(Math.max(.0001,scale));r.bud.visible=visibility>.0001;
    r.ornament.position.copy(r.end);r.ornament.scale.setScalar(Math.max(.0001,scale));r.ornament.visible=visibility>.0001;
    r.mat.emissiveIntensity=selected===null?.18:selected===r.slot?.72:.035;r.leafMat.emissiveIntensity=selected===r.slot?.42:.09;
  }
  wind.value=reduced.matches?0:(now-pausedDuration)*.0007;controls.update(dt);placeLabels();
  renderer.info.reset();composer.render();renderedFrames++;
  const cpuMs=performance.now()-cpuStart;
  if(delta>0&&delta<2000)intervals.push(delta);if(intervals.length>150)intervals.shift();
  if(now-lastStatus>600) {
    const fps=intervals.length?1000/(intervals.reduce((a,b)=>a+b,0)/intervals.length):0;
    $('render-status').textContent=`${width} × ${height} · ${Math.round(fps)} fps · 4× AA`;
    $('render-status').dataset.frames=String(renderedFrames);
    lastStatus=now;
  }
  if(sample&&now>=sample.start) {
    // The initial frame crosses the warmup boundary and is not a full sample interval.
    if(sample.previous!==undefined){sample.frames.push(now-sample.previous);sample.cpu.push(cpuMs);}sample.previous=now;
    $('measurement').textContent=`Measuring… ${Math.min(10,Math.floor((now-sample.start)/1000))}/10s`;
    if(now-sample.start>=10000) {
      const gl=renderer.getContext(), ext=gl.getExtension('WEBGL_debug_renderer_info');
      report={...frameStats(sample.frames),width,height,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,three:THREE.REVISION,visible:!document.hidden,
        cpuMeanMs:+(sample.cpu.reduce((a,b)=>a+b,0)/sample.cpu.length).toFixed(2),gpu:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER),geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures};
      $('measurement').dataset.report=JSON.stringify(report);
      const avg=sample.frames.reduce((a,b)=>a+b,0)/sample.frames.length;
      const p95=report.p95Ms;
      $('measurement').textContent=`${(1000/avg).toFixed(1)} fps · p95 ${p95.toFixed(1)} ms`;
      $('measure').disabled=false;sample=null;
    }
  }
}
paintUI();records.forEach(r=>{updateLeaves(r,1);setOrnaments(r);});orbitState();resize();$('loading').hidden=true;frameId=requestAnimationFrame(frame);
addEventListener('pagehide',event=>{if(!event.persisted){cancelAnimationFrame(frameId);renderer.dispose();composer.dispose();env.dispose();}});
