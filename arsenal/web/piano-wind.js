import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {buildEnvelope,envelopeAt,makeSeeds,flowPoint,normalizeSettings,DEFAULTS,LOOKS,FLOW_START,FLOW_END,CAR_LENGTH} from './piano/wind-flow.mjs';
import {bufferSize} from './piano/gyre-motion.mjs';
import {frameStats} from './piano/crystal-performance.mjs';
import {createWindTunnel} from './piano/wind-tunnel.mjs';

const $=id=>document.getElementById(id),params=new URLSearchParams(location.search);
const fluidMode=document.body.dataset.flow==='fluid';let tunnel=null,flowBlend=1;
let state=normalizeSettings({...DEFAULTS,...Object.fromEntries(params)}),time=15,last=0,raf=0,frames=0,ready=false;
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches,orbit=false,view='hero',sample=null,intervals=[],statusAt=0;
const canvas=$('stage'),viewport=$('viewport');
const fail=e=>{$('error').hidden=false;$('error').textContent='The study could not render: '+(e.message||e);$('loading').hidden=true;setPaused(true);};
addEventListener('error',e=>fail(e.error||e.message));addEventListener('unhandledrejection',e=>fail(e.reason));
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});
renderer.setPixelRatio(1);renderer.setClearColor(0x070912,0);renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;
renderer.debug.onShaderError=(gl,p,v,f)=>fail(new Error(gl.getShaderInfoLog(v)+' '+gl.getShaderInfoLog(f)));
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,.06,100);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=!paused;controls.dampingFactor=.06;controls.enablePan=false;
controls.minDistance=4;controls.maxDistance=25;controls.maxPolarAngle=Math.PI*.49;controls.autoRotateSpeed=.35;
scene.add(new THREE.HemisphereLight(0xc5c5ff,0x20182d,.8));
function directional(color,intensity,position){const l=new THREE.DirectionalLight(color,intensity);l.position.set(...position);scene.add(l);}
directional(0xece7ff,1.8,[0,7,3]);directional(0xbf72ff,2,[1,2,-4]);directional(0x7696ff,1.2,[-5,2,1]);
const pmrem=new THREE.PMREMGenerator(renderer),room=new RoomEnvironment();
const environment=pmrem.fromScene(room,.04);scene.environment=environment.texture;scene.environmentIntensity=.8;room.dispose();pmrem.dispose();
// A quiet matte stage keeps the studio environment's bright reflection cards on the car.
const floor=new THREE.Mesh(new THREE.PlaneGeometry(60,60),new THREE.ShaderMaterial({transparent:true,depthWrite:false,
vertexShader:'varying vec3 vWorld;void main(){vec4 p=modelMatrix*vec4(position,1.);vWorld=p.xyz;gl_Position=projectionMatrix*viewMatrix*p;}',
fragmentShader:'varying vec3 vWorld;void main(){float r=length(vWorld.xz);float pool=exp(-dot(vWorld.xz*vec2(.16,.34),vWorld.xz*vec2(.16,.34)));vec3 c=mix(vec3(.0025,.003,.006),vec3(.009,.004,.016),pool);gl_FragColor=vec4(c,1.-smoothstep(8.,23.,r));\n#include <colorspace_fragment>\n}'}));
floor.rotation.x=-Math.PI/2;floor.position.y=-.025;scene.add(floor);
const shadow=new THREE.Mesh(new THREE.PlaneGeometry(6.7,4.1),new THREE.ShaderMaterial({transparent:true,depthWrite:false,
vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',
fragmentShader:'varying vec2 vUv;void main(){vec2 p=(vUv-.5)*2.;float a=exp(-dot(p,p)*3.6)*.8;gl_FragColor=vec4(.002,.001,.008,a);}'}));
shadow.rotation.x=-Math.PI/2;shadow.position.y=.002;scene.add(shadow);
const linePositions=[];
for(let z of [-2.65,2.65])for(let x=-7;x<9;x+=.55)linePositions.push(x,.005,z,x+.13,.005,z);
const guideGeometry=new THREE.BufferGeometry();guideGeometry.setAttribute('position',new THREE.Float32BufferAttribute(linePositions,3));
scene.add(new THREE.LineSegments(guideGeometry,new THREE.LineBasicMaterial({color:0x65577d,transparent:true,opacity:.18})));

const MAX_STREAMS=108,SEGMENTS=384,SPARKS_PER_STREAM=62,ROWS=MAX_STREAMS;
const pathData=new Float32Array((SEGMENTS+1)*ROWS*4);
const pathTexture=new THREE.DataTexture(pathData,SEGMENTS+1,ROWS,THREE.RGBAFormat,THREE.FloatType);
pathTexture.minFilter=pathTexture.magFilter=THREE.NearestFilter;pathTexture.generateMipmaps=false;
const previousData=new Float32Array(pathData.length),previousTexture=new THREE.DataTexture(previousData,SEGMENTS+1,ROWS,THREE.RGBAFormat,THREE.FloatType);
previousTexture.minFilter=previousTexture.magFilter=THREE.NearestFilter;previousTexture.generateMipmaps=false;
const U={uTime:{value:time},uSpeed:{value:state.speed},uTrail:{value:state.trail},uWake:{value:state.wake},uSize:{value:new THREE.Vector2(1,1)},uWidth:{value:2.2},uOpacity:{value:.7},uPaths:{value:pathTexture},uPreviousPaths:{value:previousTexture},uFlowBlend:{value:1},uSignal:{value:0}};
const positions=new Float32Array(MAX_STREAMS*(SEGMENTS+1)*2*3),nexts=new Float32Array(positions.length);
const previousPositions=new Float32Array(positions.length),previousNexts=new Float32Array(positions.length),signals=new Float32Array(positions.length/3);
const sides=new Float32Array(positions.length/3),progress=new Float32Array(sides.length),lanes=new Float32Array(sides.length);
const indices=new Uint32Array(MAX_STREAMS*SEGMENTS*6);
for(let l=0;l<MAX_STREAMS;l++)for(let j=0;j<=SEGMENTS;j++)for(let s=0;s<2;s++){
  const k=(l*(SEGMENTS+1)+j)*2+s;sides[k]=s?1:-1;progress[k]=j/SEGMENTS;lanes[k]=l;
  if(!s&&j<SEGMENTS)indices.set([k,k+2,k+1,k+1,k+2,k+3],(l*SEGMENTS+j)*6);
}
const geometry=new THREE.BufferGeometry();
for(const [name,array,size] of [['position',positions,3],['aNext',nexts,3],['aSide',sides,1],['aProgress',progress,1],['aLane',lanes,1]])geometry.setAttribute(name,new THREE.BufferAttribute(array,size));
for(const [name,array,size] of [['aPrevious',previousPositions,3],['aPreviousNext',previousNexts,3],['aSignal',signals,1]])geometry.setAttribute(name,new THREE.BufferAttribute(array,size));
geometry.setIndex(new THREE.BufferAttribute(indices,1));
const common=`
uniform float uTime,uSpeed,uTrail,uWake;uniform vec2 uSize;
varying float vSide,vProgress,vLane,vFade,vSignal;
vec3 drift(vec3 p,float lane){
  float a=smoothstep(2.7,7.,p.x)*uWake;
  p.y+=a*(.075+.07*sin(p.x*1.5-uTime*.6+lane*.37));
  p.z+=a*.1*sin(p.x*1.8-uTime*.7+lane*.31);
  return p;
}
`;
const ribbons=new THREE.Mesh(geometry,new THREE.ShaderMaterial({uniforms:U,transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending,toneMapped:false,
vertexShader:common+`
attribute vec3 aNext,aPrevious,aPreviousNext;attribute float aSide,aProgress,aLane,aSignal;uniform float uWidth,uFlowBlend;
void main(){
 vec4 p=modelViewMatrix*vec4(drift(mix(aPrevious,position,uFlowBlend),aLane),1.),q=modelViewMatrix*vec4(drift(mix(aPreviousNext,aNext,uFlowBlend),aLane),1.);
 vFade=smoothstep(.1,.5,-p.z);p.z=min(p.z,-.06);q.z=min(q.z,-.06);
 vec4 cp=projectionMatrix*p,cq=projectionMatrix*q;
 vec2 d=(cq.xy/cq.w-cp.xy/cp.w)*uSize;vec2 n=vec2(-d.y,d.x)/max(length(d),.0001);
 cp.xy+=n*aSide*uWidth*2./uSize*cp.w;gl_Position=cp;
 vSide=aSide;vProgress=aProgress;vLane=aLane;vSignal=aSignal;
}`,
fragmentShader:`
uniform float uTime,uSpeed,uTrail,uOpacity,uSignal;varying float vSide,vProgress,vLane,vFade,vSignal;
void main(){
 float phase=fract(uTime*uSpeed*.055+vLane*.173-vProgress);
 float tail=1.-smoothstep(uTrail*.18,uTrail*.9,phase);
 float edge=smoothstep(0.,.06,vProgress)*(1.-smoothstep(.84,1.,vProgress));
 float flicker=mix(1.,.22+.78*smoothstep(-.7,.6,sin(vProgress*210.+vLane*19.+uTime*2.)),smoothstep(.57,1.,phase)*.7);
 float core=exp(-vSide*vSide*32.),halo=exp(-vSide*vSide*4.)*.25;
 float alpha=(core+halo)*(.17+tail*.9)*edge*vFade*flicker*uOpacity;
 vec3 c=mix(vec3(.26,.14,1.),vec3(.9,.24,.65),.5+.5*sin(vLane*.63+vProgress*4.));
 c=mix(c,vec3(.72,.75,1.),pow(max(0.,1.-phase*8.),3.)*.65);
 if(uSignal>.5)c=mix(mix(vec3(.13,.15,.8),vec3(.68,.28,1.),smoothstep(.1,1.1,vSignal)),vec3(1.,.82,.51),smoothstep(1.1,1.7,vSignal));
 if(alpha<.002)discard;gl_FragColor=vec4(c,alpha);
 #include <colorspace_fragment>
}`}));
ribbons.frustumCulled=false;scene.add(ribbons);
const sparkLane=new Float32Array(MAX_STREAMS*SPARKS_PER_STREAM),sparkPhase=new Float32Array(sparkLane.length);
for(let i=0;i<sparkLane.length;i++){sparkLane[i]=Math.floor(i/SPARKS_PER_STREAM);sparkPhase[i]=(i%SPARKS_PER_STREAM)/SPARKS_PER_STREAM;}
const sparkGeometry=new THREE.BufferGeometry();sparkGeometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(sparkLane.length*3),3));sparkGeometry.setAttribute('aLane',new THREE.BufferAttribute(sparkLane,1));sparkGeometry.setAttribute('aPhase',new THREE.BufferAttribute(sparkPhase,1));
const sparks=new THREE.Points(sparkGeometry,new THREE.ShaderMaterial({uniforms:U,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false,
vertexShader:common+`
uniform sampler2D uPaths,uPreviousPaths;uniform float uFlowBlend;attribute float aLane,aPhase;
void main(){
 float p=fract(uTime*uSpeed*.055+aLane*.173-aPhase*uTrail),column=p*384.,i=floor(column);
 vec3 a=texture2D(uPaths,vec2((i+.5)/385.,(aLane+.5)/108.)).xyz;
 vec3 b=texture2D(uPaths,vec2((min(i+1.,384.)+.5)/385.,(aLane+.5)/108.)).xyz;
 vec3 oldA=texture2D(uPreviousPaths,vec2((i+.5)/385.,(aLane+.5)/108.)).xyz;
 vec3 oldB=texture2D(uPreviousPaths,vec2((min(i+1.,384.)+.5)/385.,(aLane+.5)/108.)).xyz;
 a=mix(oldA,a,uFlowBlend);b=mix(oldB,b,uFlowBlend);
 vec4 mv=modelViewMatrix*vec4(drift(mix(a,b,fract(column)),aLane),1.);
 gl_Position=projectionMatrix*mv;gl_PointSize=clamp(uSize.y*.12/max(1.,-mv.z),2.5,uSize.y*.06)*(1.-aPhase*.5);
 vProgress=p;vLane=aLane;vSide=aPhase;vFade=smoothstep(.1,.5,-mv.z)*pow(1.-aPhase,.7);
 vSignal=texture2D(uPaths,vec2((i+.5)/385.,(aLane+.5)/108.)).w;
}`,
fragmentShader:`
uniform float uTime,uTrail,uSignal;varying float vProgress,vLane,vFade,vSide,vSignal;
void main(){
 vec2 q=gl_PointCoord*2.-1.;float r=dot(q,q);if(r>1.)discard;
 float edge=smoothstep(0.,.06,vProgress)*(1.-smoothstep(.86,1.,vProgress));
 float glint=.4+.6*pow(.5+.5*sin(vLane*17.+vProgress*170.-uTime*.3),3.);
 float end=mix(1.,.15+.85*smoothstep(-.6,.6,sin(vProgress*330.+vLane*7.+uTime*2.)),smoothstep(.45,1.,vSide));
 vec3 c=mix(vec3(.5,.38,1.),vec3(1.,.48,.8),.5+.5*sin(vLane*.63+vProgress*4.));
 if(uSignal>.5)c=mix(mix(vec3(.13,.15,.8),vec3(.68,.28,1.),smoothstep(.1,1.1,vSignal)),vec3(1.,.82,.51),smoothstep(1.1,1.7,vSignal));
 gl_FragColor=vec4(c,(exp(-r*22.)+exp(-r*4.)*.2)*edge*glint*vFade*end*1.8);
 #include <colorspace_fragment>
}`}));
sparks.frustumCulled=false;scene.add(sparks);
let envelope=null,bodyMaterials=[],carGroup=null;
let receivedPaths=false,receivedCount=0;
function acceptFluidPaths(data,diagnostics,previousOverride=null){
 const count=data.length/((SEGMENTS+1)*4),same=receivedPaths&&count===receivedCount;
 previousPositions.set(positions);previousNexts.set(nexts);previousData.set(pathData);pathData.fill(0);pathData.set(data);
 for(let l=0;l<count;l++)for(let j=0;j<=SEGMENTS;j++)for(let s=0;s<2;s++){
  const k=((l*(SEGMENTS+1)+j)*2+s)*3,p=(l*(SEGMENTS+1)+j)*4,q=(l*(SEGMENTS+1)+Math.min(j+1,SEGMENTS))*4;
  for(let a=0;a<3;a++){positions[k+a]=data[p+a];nexts[k+a]=j===SEGMENTS?data[p+a]*2-data[p-4+a]:data[q+a];}signals[k/3]=data[p+3];
 }
 if(!same){previousPositions.set(positions);previousNexts.set(nexts);previousData.set(pathData);}
 if(previousOverride){
  previousData.set(previousOverride);
  for(let l=0;l<count;l++)for(let j=0;j<=SEGMENTS;j++)for(let s=0;s<2;s++){
   const k=((l*(SEGMENTS+1)+j)*2+s)*3,p=(l*(SEGMENTS+1)+j)*4,q=(l*(SEGMENTS+1)+Math.min(j+1,SEGMENTS))*4;
   for(let a=0;a<3;a++){previousPositions[k+a]=previousOverride[p+a];previousNexts[k+a]=j===SEGMENTS?previousOverride[p+a]*2-previousOverride[p-4+a]:previousOverride[q+a];}
  }
 }
 for(const name of ['position','aNext','aPrevious','aPreviousNext','aSignal'])geometry.attributes[name].needsUpdate=true;
 pathTexture.needsUpdate=previousTexture.needsUpdate=true;flowBlend=same?0:1;U.uFlowBlend.value=flowBlend;
 geometry.setDrawRange(0,count*SEGMENTS*6);sparkGeometry.setDrawRange(0,count*SPARKS_PER_STREAM);receivedPaths=true;receivedCount=count;
 canvas.dataset.flowChecks=JSON.stringify({samples:count*(SEGMENTS+1),minSurfaceDistance:diagnostics.minDistance,requestedClearance:diagnostics.clearance});
 if(ready&&paused&&!previousOverride){flowBlend=1;draw();}
}
function rebuild(){
 if(fluidMode){tunnel?.configure(state);return;}
 if(!envelope)return;
 const seeds=makeSeeds(state.density),p=[0,0,0],q=[0,0,0];
 for(let l=0;l<state.density;l++)for(let j=0;j<=SEGMENTS;j++){
  flowPoint(j/SEGMENTS,seeds[l],envelope,state,p);flowPoint(Math.min(1,(j+1)/SEGMENTS),seeds[l],envelope,state,q);
  if(j===SEGMENTS){flowPoint((j-1)/SEGMENTS,seeds[l],envelope,state,q);for(let a=0;a<3;a++)q[a]=p[a]+(p[a]-q[a]);}
  for(let s=0;s<2;s++){const k=((l*(SEGMENTS+1)+j)*2+s)*3;positions.set(p,k);nexts.set(q,k);}
  pathData.set([...p,1],(l*(SEGMENTS+1)+j)*4);
 }
 geometry.attributes.position.needsUpdate=geometry.attributes.aNext.needsUpdate=true;pathTexture.needsUpdate=true;
 geometry.setDrawRange(0,state.density*SEGMENTS*6);sparkGeometry.setDrawRange(0,state.density*SPARKS_PER_STREAM);
 let minGap=Infinity;
 for(const seed of seeds)for(let i=0;i<=80;i++){
  const x=envelope.minX+(envelope.maxX-envelope.minX)*i/80;
  flowPoint((x-FLOW_START)/(FLOW_END-FLOW_START),seed,envelope,state,p);const [w,h]=envelopeAt(x,envelope);
  minGap=Math.min(minGap,Math.max(p[1]-h,Math.abs(p[2])-w));
 }
 canvas.dataset.flowChecks=JSON.stringify({bodySamples:seeds.length*81,minEnvelopeGap:minGap,requestedClearance:state.clearance});
}
function applyPaint(){
 for(const m of bodyMaterials){m.color.set(state.paint==='pearl'?0x646079:0x271c40);m.metalness=state.paint==='pearl'?.7:.78;m.roughness=state.paint==='pearl'?.27:.24;m.clearcoat=1;m.clearcoatRoughness=.16;m.envMapIntensity=.85;m.normalScale.set(.06,.06);}
}
function updateUrl(){
 const u=new URL(location.href);for(const [k,v] of Object.entries(state))u.searchParams.set(k,String(v));u.searchParams.set('resolution',$('resolution').value);history.replaceState(null,'',u);
}
function cancelMeasurement(){sample=null;$('measurement').textContent='';delete $('measurement').dataset.report;$('measure').disabled=paused||!ready;}
function sync(rebuildPaths=true){
 state=normalizeSettings(state);
 document.querySelectorAll('[data-look]').forEach(b=>{const look=normalizeSettings(LOOKS[b.dataset.look]);b.setAttribute('aria-pressed',String(Object.keys(state).every(k=>state[k]===look[k])));});
 for(const id of ['speed','trail','clearance','wake']){$(id).value=state[id];$(id+'-value').textContent=id==='speed'?state[id].toFixed(2)+'×':id==='clearance'?state[id].toFixed(2):Math.round(state[id]*100)+'%';}
 for(const id of ['density','style','paint'])$(id).value=String(state[id]);
 U.uSpeed.value=state.speed;U.uTrail.value=state.trail;U.uWake.value=fluidMode?0:state.wake;U.uOpacity.value=fluidMode?(state.style==='mixed'?.7:.9):(state.style==='mixed'?.95:1.2);
 ribbons.visible=state.style!=='sparks';sparks.visible=state.style!=='silk';
 if(rebuildPaths)rebuild();applyPaint();updateUrl();cancelMeasurement();if(ready)draw();
}
function setView(id){
 view=id;orbit=false;controls.autoRotate=false;$('orbit').setAttribute('aria-pressed','false');
 const views={hero:[-6.3,2.7,7.2],side:[.3,2.0,9.6],top:[.8,10,.001],wake:[8.8,2.4,5.5]};
 camera.up.set(0,1,0);camera.position.set(...views[id]);controls.target.set(id==='wake'?1.8:.4,.65,0);
 const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;
 document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===id)));
 cancelMeasurement();if(ready)draw();
}
let size=[1,1],dpr=devicePixelRatio;
function resize(){
 const rect=viewport.getBoundingClientRect();size=bufferSize(rect.width,rect.height,devicePixelRatio,$('resolution').value);
 renderer.setSize(...size,false);camera.aspect=rect.width/rect.height;camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(38*Math.PI/360)*Math.max(1,1.35/camera.aspect)));camera.updateProjectionMatrix();U.uSize.value.set(...size);
 U.uWidth.value=Math.max(1.5,size[1]/750*2.2);dpr=devicePixelRatio;cancelMeasurement();if(ready)draw();status(0);
}
function draw(){
 if(!ready)return;U.uTime.value=time;U.uFlowBlend.value=tunnel?.playback?flowBlend:flowBlend*flowBlend*(3-2*flowBlend);renderer.render(scene,camera);frames++;
 canvas.dataset.frames=String(frames);canvas.dataset.drawCalls=String(renderer.info.render.calls);canvas.dataset.triangles=String(renderer.info.render.triangles);canvas.dataset.geometries=String(renderer.info.memory.geometries);canvas.dataset.textures=String(renderer.info.memory.textures);
}
function status(fps){$('status').textContent=size.join(' × ')+' · '+(paused?'paused':Math.round(fps)+' fps')+' · MSAA';}
function frame(now){
 raf=0;if(paused||document.hidden)return;
 const dt=last?(now-last)/1000:0;last=now;time+=Math.min(dt,.08);
 if(tunnel?.playback)tunnel.tick(Math.min(dt,.08));else{flowBlend=Math.min(1,flowBlend+dt/.45);tunnel?.tick(Math.min(dt,.08));}
 if(dpr!==devicePixelRatio)resize();controls.autoRotate=orbit;controls.update();draw();
 if(dt>0&&dt<.2)intervals.push(dt*1000);if(intervals.length>180)intervals.shift();
 if(sample&&now>=sample.start){if(dt>0)sample.times.push(dt*1000);if(now>=sample.end){
  const gl=renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');
  const report={...frameStats(sample.times),buffer:size.slice(),msaa:gl.getParameter(gl.SAMPLES),gpu:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):'unavailable',drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,settings:{...state},solver:fluidMode?JSON.parse(canvas.dataset.solver||'null'):undefined};
  report.over16_9Frames=sample.times.filter(ms=>ms>16.9).length;
  $('measurement').textContent=report.fps+' fps · p95 '+report.p95Ms+' ms';$('measurement').dataset.report=JSON.stringify(report);sample=null;$('measure').disabled=false;
 }}
 if(now-statusAt>700){const f=frameStats(intervals);status(f?.fps||0);statusAt=now;}
 raf=requestAnimationFrame(frame);
}
function setPaused(value){
 paused=value;cancelAnimationFrame(raf);raf=0;last=0;controls.enableDamping=!paused;
 $('pause').textContent=paused?'Resume render':'Pause render';$('pause').setAttribute('aria-pressed',String(paused));cancelMeasurement();status(0);
 tunnel?.setRunning(!paused&&!document.hidden);
 if(!paused&&!document.hidden&&ready)raf=requestAnimationFrame(frame);
}
for(const id of ['speed','trail','clearance','wake'])$(id).addEventListener('input',()=>{state[id]=Number($(id).value);document.querySelectorAll('[data-look]').forEach(b=>b.setAttribute('aria-pressed','false'));sync(['clearance','wake'].includes(id));});
for(const id of ['density','style','paint'])$(id).addEventListener('change',()=>{state[id]=id==='density'?Number($(id).value):$(id).value;sync(id==='density');});
document.querySelectorAll('[data-look]').forEach(b=>b.addEventListener('click',()=>{state={...LOOKS[b.dataset.look]};document.querySelectorAll('[data-look]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));sync();}));
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>setView(b.dataset.view)));
$('orbit').addEventListener('click',()=>{orbit=!orbit;$('orbit').setAttribute('aria-pressed',String(orbit));cancelMeasurement();});
controls.addEventListener('start',()=>{orbit=false;$('orbit').setAttribute('aria-pressed','false');cancelMeasurement();});
controls.addEventListener('change',()=>{if(paused)draw();});
$('pause').addEventListener('click',()=>setPaused(!paused));
$('resolution').value=params.get('resolution')==='4k'?'4k':'native';
$('resolution').addEventListener('change',()=>{updateUrl();resize();});
$('measure').addEventListener('click',()=>{if(!ready||paused)return;const n=performance.now();sample={start:n+1000,end:n+11000,times:[]};$('measure').disabled=true;$('measurement').textContent='Measuring after warmup…';delete $('measurement').dataset.report;});
$('copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(location.href);$('message').textContent='Link copied. It preserves the flow controls and finish.';}catch{$('message').textContent='Copy the address bar to keep this look.';}});
$('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){$('message').textContent=e.message;}});
document.addEventListener('visibilitychange',()=>{last=0;cancelMeasurement();cancelAnimationFrame(raf);raf=0;tunnel?.setRunning(!paused&&!document.hidden);if(!paused&&!document.hidden&&ready)raf=requestAnimationFrame(frame);});
addEventListener('pagehide',()=>tunnel?.dispose());
if(fluidMode){
 $('yaw').addEventListener('input',cancelMeasurement);
 const colour=$('flow-colour');colour.value=params.get('colour')==='speed'?'speed':'violet';U.uSignal.value=colour.value==='speed'?1:0;
 colour.addEventListener('change',()=>{U.uSignal.value=colour.value==='speed'?1:0;const url=new URL(location.href);url.searchParams.set('colour',colour.value);history.replaceState(null,'',url);cancelMeasurement();if(ready)draw();});
}
new ResizeObserver(resize).observe(viewport);
setView('hero');resize();sync(false);

async function loadCar(){
 const gltf=await new GLTFLoader().loadAsync('./assets/car-concept/CarConcept.glb');
 const wrapper=new THREE.Group();wrapper.add(gltf.scene);wrapper.updateMatrixWorld(true);
 let bounds=new THREE.Box3().setFromObject(wrapper),center=bounds.getCenter(new THREE.Vector3());
 const headlights=gltf.scene.getObjectByName('BodyHeadlights');
 const front=new THREE.Box3().setFromObject(headlights).getCenter(new THREE.Vector3()).sub(center);
 wrapper.rotation.y=Math.atan2(front.z,front.x)-Math.PI;wrapper.updateMatrixWorld(true);
 bounds.setFromObject(wrapper);wrapper.scale.setScalar(CAR_LENGTH/(bounds.max.x-bounds.min.x));wrapper.updateMatrixWorld(true);
 bounds.setFromObject(wrapper);center=bounds.getCenter(new THREE.Vector3());wrapper.position.set(-center.x,-bounds.min.y,-center.z);wrapper.updateMatrixWorld(true);
 const points=[],triangleParts=[],v=new THREE.Vector3(),materials=new Map(),buckets=new Map();
 wrapper.traverse(o=>{if(!o.isMesh)return;
   let m=materials.get(o.material.uuid);
   if(!m){m=o.material.clone();materials.set(o.material.uuid,m);
     if(m.name?.startsWith('Paint'))bodyMaterials.push(m);
     if(m.transmission>0){m.transmission=0;m.transparent=true;m.opacity=.88;m.color.set(0x162132);m.roughness=.1;m.metalness=.2;m.depthWrite=true;}
     if(m.name==='Headlight'){m.emissive.set(0xa4acff);m.emissiveIntensity=1.7;}
     for(const k of ['map','normalMap','roughnessMap','metalnessMap','aoMap'])if(m[k])m[k].anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
   }
   const g=o.geometry.clone().applyMatrix4(o.matrixWorld),a=g.attributes.position;
   for(let i=0;i<a.count;i++){v.fromBufferAttribute(a,i);points.push([v.x,v.y,v.z]);}
   if(fluidMode){const ix=g.index,part=new Float32Array((ix?ix.count:a.count)*3);for(let i=0;i<part.length/3;i++){const k=ix?ix.getX(i):i;part[i*3]=a.getX(k);part[i*3+1]=a.getY(k);part[i*3+2]=a.getZ(k);}triangleParts.push(part);}
   const key=m.uuid+':'+Object.keys(g.attributes).sort().join(',')+':'+!!g.index;
   if(!buckets.has(key))buckets.set(key,{m,gs:[]});buckets.get(key).gs.push(g);
 });
 carGroup=new THREE.Group();let mergedCount=0;
 for(const {m,gs} of buckets.values()){const g=mergeGeometries(gs,false);if(!g)throw new Error('Car geometry could not be assembled');carGroup.add(new THREE.Mesh(g,m));mergedCount++;for(const old of gs)old.dispose();}
 scene.add(carGroup);applyPaint();
 envelope=buildEnvelope(points,-CAR_LENGTH/2,CAR_LENGTH/2);
 canvas.dataset.model=JSON.stringify({name:'Car Concept',sourceVertices:points.length,mergedMeshes:mergedCount,envelopeBins:envelope.widths.length,length:CAR_LENGTH,height:points.reduce((h,p)=>Math.max(h,p[1]),0)});
 // Original geometry is replaced by material-grouped static meshes.
 wrapper.traverse(o=>{if(o.isMesh)o.geometry.dispose();});
 if(fluidMode){
  const triangles=new Float32Array(triangleParts.reduce((n,a)=>n+a.length,0));let offset=0;for(const part of triangleParts){triangles.set(part,offset);offset+=part.length;}
  tunnel=createWindTunnel({triangles,settings:state,onPaths:acceptFluidPaths,onError:fail,
   onReplayFrame:(a,b)=>acceptFluidPaths(b,{recorded:true},a),onReplayTime:(alpha,phase)=>{flowBlend=alpha;time=phase;},
   getScene:()=>({settings:{...state},phase:time,colour:$('flow-colour').value,camera:{position:camera.position.toArray(),target:controls.target.toArray(),up:camera.up.toArray()}}),
   restoreScene:meta=>{
    state=normalizeSettings(meta.settings);sync(false);U.uSignal.value=meta.colour==='speed'?1:0;$('flow-colour').value=meta.colour==='speed'?'speed':'violet';
    const c=meta.camera,valid=v=>Array.isArray(v)&&v.length===3&&v.every(n=>Number.isFinite(n)&&Math.abs(n)<100);
    if(c&&valid(c.position)&&valid(c.target)&&valid(c.up)){
     camera.position.fromArray(c.position);controls.target.fromArray(c.target);camera.up.fromArray(c.up);const damping=controls.enableDamping;controls.enableDamping=false;controls.update();controls.enableDamping=damping;
     document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed','false'));
    }
    cancelMeasurement();
   },requestPause:setPaused,onDraw:draw
  });await tunnel.ready;
 }
 ready=true;if(!fluidMode)rebuild();$('loading').hidden=true;resize();setPaused(paused);draw();
}
loadCar().catch(fail);
