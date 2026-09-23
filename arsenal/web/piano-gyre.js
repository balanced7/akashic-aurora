import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { PRESETS, WORLD_DEFAULTS, emitterAt, riderPose, anglesAt, bufferSize } from './piano/gyre-motion.mjs';
import { frameStats } from './piano/crystal-performance.mjs';
import { loadPresets, savePreset } from './piano/gyre-presets.mjs';
import { mountGyreMusic } from './piano/gyre-music.js';
import {RAY_DEFAULTS,RAY_STYLES,RAY_NOTES,createRayMeshes} from './piano/gyre-light-rays.mjs';
import {FLIGHT_DEFAULTS,FLIGHT_RANGES,FORMATIONS} from './piano/gyre-flight-motion.mjs';
import {createFlight} from './piano/gyre-flight.js';

const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const fail = error => { $('error').hidden=false; $('error').textContent=String(error?.message||error); $('loading').hidden=true; };
addEventListener('error',e=>fail(e.error||e.message));
addEventListener('unhandledrejection',e=>fail(e.reason));
let state={...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,motion:'axial',stem:3.25,reach:1.6,tail:'fade',tailAmount:.75,tailRate:6,...(PRESETS[params.get('study')]||PRESETS.silk)};
const sliders=['spin','precession','tilt','wobble','memory','pulse','stem','reach','tailAmount','tailRate','weave','petals','wind','turbulence','raySpread','radiance',...Object.keys(FLIGHT_RANGES)];
for(const id of sliders)if(params.has(id)){
  const value=Number(params.get(id)),input=$(id);
  if(Number.isFinite(value))state[id]=Math.max(Number(input.min),Math.min(Number(input.max),value));
}
for(const [id,values] of Object.entries({style:['silk','beads','sparks',...RAY_STYLES],palette:['tide','prism','ember','violet','opal'],tail:['fade','flicker','dissolve'],motion:['axial','sweep'],sculpture:['gyre','braid','pendulum'],view:['outside','ride','chase','pilot'],formation:FORMATIONS}))if(values.includes(params.get(id)))state[id]=params.get(id);
if(params.has('reactive'))state.reactive=params.get('reactive')==='true';
if(params.has('blackout'))state.blackout=params.get('blackout')==='true';
if(params.has('flightEnabled'))state.flightEnabled=params.get('flightEnabled')==='true';
if([5,9,13].includes(Number(params.get('flightCount'))))state.flightCount=Number(params.get('flightCount'));
if(['chase','pilot'].includes(state.view))state.flightEnabled=true;
if([12,18,24,32,40].includes(Number(params.get('count'))))state.count=Number(params.get('count'));
let time=31, clearedAt=time-state.memory, paused=reduced.matches, raf=0, last=0, frames=0, statusAt=0;
let sample=null, report=null, intervals=[], size=[1,1], orbit=false;
const harmony=[0,0,0],harmonyGoal=[0,0,0];let music=null,updatingCamera=false;
const canvas=$('stage'), viewport=$('viewport');
const renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:true,powerPreference:'high-performance'});
renderer.setPixelRatio(1); renderer.setClearColor(0x05090f,0);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.toneMapping=THREE.ACESFilmicToneMapping; renderer.toneMappingExposure=1.15;
renderer.debug.onShaderError=(gl,program,vertex,fragment)=>fail(`Shader error: ${gl.getShaderInfoLog(vertex)} ${gl.getShaderInfoLog(fragment)}`);
const scene=new THREE.Scene(), camera=new THREE.PerspectiveCamera(39,1,.08,220);
const controls=new OrbitControls(camera,canvas);
controls.enableDamping=!paused; controls.dampingFactor=.07; controls.enablePan=false;
controls.minDistance=8; controls.maxDistance=30; controls.autoRotateSpeed=.4;
function home() {camera.up.set(0,1,0);if(state.sculpture==='gyre')camera.position.set(10,6.3,13.5).multiplyScalar(Math.max(1,Math.hypot(state.stem,state.reach)/3.63));else camera.position.set(7.6,8,10.8);controls.target.set(0,.3,0);updatingCamera=true;controls.update();updatingCamera=false;}
home();
const outsidePosition=camera.position.clone(),outsideTarget=controls.target.clone();let activeView='outside';
scene.add(new THREE.HemisphereLight(0xb4e2f5,0x122537,2.8));
const key=new THREE.DirectionalLight(0xd9f4ff,4);key.position.set(3,7,6);scene.add(key);
const fill=new THREE.DirectionalLight(0x73baa7,2);fill.position.set(-6,1,-3);scene.add(fill);
const mechanism=new THREE.Group();scene.add(mechanism);
const precess=new THREE.Group(), tilted=new THREE.Group(), rotor=new THREE.Group(), arm=new THREE.Group();
mechanism.add(precess);precess.add(tilted);tilted.add(rotor);rotor.add(arm);
const metal=new THREE.MeshStandardMaterial({color:0x344652,metalness:.75,roughness:.28});
const dark=new THREE.MeshStandardMaterial({color:0x152431,metalness:.6,roughness:.34});
function rod(a,b,r,parent=arm,mat=metal) {
  const from=new THREE.Vector3(...a), to=new THREE.Vector3(...b), delta=to.clone().sub(from);
  const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r,delta.length(),32),mat);
  mesh.position.copy(from).add(to).multiplyScalar(.5);mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());parent.add(mesh);return mesh;
}
const stemRod=rod([0,0,0],[3.25,0,0],.034), bendRod=rod([3.25,0,0],[3.25,0,1.6],.034);
rod([0,-.38,0],[0,.38,0],.065,tilted);rod([0,0,0],[0,5.4,0],.008,mechanism);
const hub=new THREE.Mesh(new THREE.SphereGeometry(.13,24,16),metal);tilted.add(hub);
const cap=new THREE.Mesh(new THREE.SphereGeometry(.045,16,12),new THREE.MeshBasicMaterial({color:0xb9e6da}));cap.position.y=5.4;mechanism.add(cap);
// A counterweight keeps the visible object legible as a suspended kinetic sculpture.
rod([0,0,0],[-.85,0,0],.035);
const counterweight=new THREE.Mesh(new THREE.CapsuleGeometry(.13,.26,4,12),dark);counterweight.rotation.z=Math.PI/2;counterweight.position.x=-.8;arm.add(counterweight);
const MAX_LIGHTS=40, SAMPLES=1536, SPARK_SAMPLES=1100;
const leds=new THREE.InstancedMesh(new THREE.SphereGeometry(.043,32,16),new THREE.MeshBasicMaterial({color:0xffffff,toneMapped:false}),MAX_LIGHTS);
leds.instanceMatrix.setUsage(THREE.DynamicDrawUsage);leds.frustumCulled=false;scene.add(leds);
const stringsGeometry=new THREE.BufferGeometry();stringsGeometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(18),3));
const strings=new THREE.LineSegments(stringsGeometry,new THREE.LineBasicMaterial({color:0x89c3c9,transparent:true,opacity:.23,depthWrite:false}));strings.frustumCulled=false;scene.add(strings);
const anchor=new THREE.Mesh(new THREE.TorusGeometry(.12,.018,8,32),metal);anchor.position.set(0,5.4,0);scene.add(anchor);
const scratch=new THREE.Object3D(), color=new THREE.Color(), local=[0,0,0], angles=[0,0,0];
const PALETTES={tide:[0x08e7cc,0x168cca,0x8060ff],prism:[0xff5120,0x0eee8a,0x853eff],ember:[0xff3b0b,0xff8916,0xffdc72],violet:[0x623dff,0xeb399d,0x8cafff],opal:[0x19c9bb,0x9ebaff,0xff94c5]};
const U={uTime:{value:time},uLife:{value:state.memory},uClear:{value:clearedAt},uSpin:{value:state.spin},uPrecession:{value:state.precession},uTilt:{value:state.tilt},uWobble:{value:state.wobble},uPulse:{value:state.pulse},uCount:{value:state.count},uStyle:{value:0},uSize:{value:new THREE.Vector2(1,1)},uWidth:{value:3},uA:{value:new THREE.Color()},uB:{value:new THREE.Color()},uC:{value:new THREE.Color()}};
U.uAxial={value:state.motion!=='sweep'?1:0};
for(const id of ['Stem','Reach','TailAmount','TailRate'])U['u'+id]={value:state[id[0].toLowerCase()+id.slice(1)]};
U.uTail={value:0};
U.uRaySpread={value:state.raySpread};U.uRadiance={value:state.radiance};
U.uWorld={value:0};U.uHarmony={value:new THREE.Vector3()};
for(const key of ['Weave','Petals','Wind','Turbulence'])U['u'+key]={value:state[key[0].toLowerCase()+key.slice(1)]};
const common=`
uniform float uTime,uLife,uClear,uSpin,uPrecession,uTilt,uWobble,uPulse,uCount,uStyle,uAxial,uStem,uReach,uTail,uTailAmount,uTailRate;
uniform vec2 uSize; uniform float uWidth; uniform vec3 uA,uB,uC;
uniform float uWorld,uWeave,uPetals,uWind,uTurbulence;uniform vec3 uHarmony;
attribute float aAge,aLed; varying float vSide,vFade,vPulse; varying vec3 vColor;
varying float vAge,vStamp,vLed;
const float TAU=6.28318530718;
vec3 ry(vec3 p,float a){float c=cos(a),s=sin(a);return vec3(c*p.x+s*p.z,p.y,-s*p.x+c*p.z);}
vec3 rz(vec3 p,float a){float c=cos(a),s=sin(a);return vec3(c*p.x-s*p.y,s*p.x+c*p.y,p.z);}
vec3 orient(vec3 p,float t){p=ry(p,t*TAU*uSpin);p=rz(p,radians(uTilt+uWobble*sin(t*TAU*.19)));return ry(p,t*TAU*uPrecession);}
vec3 at(float t,float led){
  float u=(led+.5)/uCount,phase=t*TAU*uSpin;vec3 p;
  if(uWorld<.5){float d=.65+u*(uStem+uReach-.65);p=vec3(min(d,uStem)*(1.-uAxial),min(d,uStem)*uAxial,max(0.,d-uStem));return orient(p,t);}
  float opening=1.+uHarmony.x*.22;
  if(uWorld<1.5){
    float strand=mod(led,3.),lane=floor(led/3.)/max(1.,ceil(uCount/3.)-1.)-.5;
    float a=phase+lane*.1,b=phase*(uPetals*.5+uHarmony.y*.3)+strand*TAU/3.+lane*.3;
    float r=(.45+uWeave*.9+lane*.18)*opening,R=1.+uReach*.5+cos(b)*r;p=vec3(R*cos(a),sin(b)*r,R*sin(a));
  }else{
    float a=phase+u*.35,R=(.6+u*.65)*(1.7+uReach*.5)*opening,petal=uPetals-1.+uHarmony.y*.15;
    p=vec3(R*(.72*cos(a)+.28*cos(petal*a)),-.8+uWeave*.9*sin(a*2.+u*2.5),R*(.72*sin(a)-.28*sin(petal*a)));
  }
  return ry(rz(p,radians(uTilt+uWobble*sin(t*TAU*.19))*.35),t*TAU*uPrecession);
}
vec3 trailAt(float t,float led,float age){
  vec3 p=at(t,led);float seconds=age*uLife,u=(led+.5)/uCount;
  float flutter=(uTurbulence+uHarmony.y*.25)*uWind*seconds*.3;
  vec3 wind=vec3(sin(uTime*1.7+u*17.+seconds*.8)*flutter,sin(uTime*.9+u*23.-seconds*.6)*flutter,-uWind*seconds*1.5);
  p+=uWorld<.5?orient(wind,uTime):wind;
  if(uTail>1.5){float drift=smoothstep(.55,1.,age)*uTailAmount*.28;float s=led*2.31+t*2.;p+=vec3(sin(s+age*5.),cos(s*.7+age*3.),sin(s*.8-age*4.))*drift;}return p;
}
float pulseAt(float t,float u){if(uPulse<.001)return 1.;float wave=.5+.5*sin(t*TAU*uPulse*(.6+u*1.7)+u*19.);return uStyle>.5 ? smoothstep(.58,.94,wave) : .45+.55*wave;}
void lightAt(float t){float u=(aLed+.5)/uCount;float h=.5+.5*sin(u*3.7+t*.14+uHarmony.z*.8);vColor=mix(mix(uA,uB,smoothstep(0.,.6,h)),uC,smoothstep(.57,1.,h));vFade=pow(max(0.,1.-aAge),mix(1.4,.8,step(.5,uTail)*uTailAmount))*smoothstep(uClear-.025,uClear+.025,t);vPulse=pulseAt(t,u);vAge=aAge;vStamp=t;vLed=aLed;}
`;
const tailFragment=`
uniform float uTime,uTail,uTailAmount,uTailRate,uRadiance;
varying float vAge,vStamp,vLed;
float hash(float x){return fract(sin(x*127.1)*43758.5453);}
float noise(float x){float i=floor(x),f=fract(x);return mix(hash(i),hash(i+1.),f*f*(3.-2.*f));}
vec2 tailFinish(){
  if(uTail<.5)return vec2(1.,0.);
  float band=smoothstep(.45,.92,vAge),phase=uTime*uTailRate;
  float flicker=noise(vStamp*11.+vLed*29.+phase);
  if(uTail<1.5)return vec2(mix(1.,.04+1.65*smoothstep(.28,.76,flicker),band*uTailAmount),0.);
  float grain=noise(vStamp*19.+vLed*37.+phase*.23),threshold=band*.96;
  float coverage=smoothstep(threshold-.08,threshold+.08,grain);
  float edge=exp(-pow((grain-threshold)*18.,2.))*band*uTailAmount;
  return vec2(mix(1.,coverage,uTailAmount)*(1.+edge*1.5),edge*.3);
}
`;
const ribbonVertex=common+`
attribute float aSide;
void main(){float t=uTime-aAge*uLife;vec4 p=modelViewMatrix*vec4(trailAt(t,aLed,aAge),1.);vec4 q=modelViewMatrix*vec4(trailAt(t+.002,aLed,max(0.,aAge-.002/uLife)),1.);float nearFade=smoothstep(.12,.5,-p.z);p.z=min(p.z,-.08);q.z=min(q.z,-.08);vec4 cp=projectionMatrix*p,cq=projectionMatrix*q;vec2 delta=(cq.xy/cq.w-cp.xy/cp.w)*uSize;vec2 perp=vec2(-delta.y,delta.x)/max(length(delta),.0001);cp.xy+=perp*aSide*uWidth*2./uSize*cp.w;gl_Position=cp;vSide=aSide;lightAt(t);vFade*=nearFade;}
`;
const ribbonFragment=`
${tailFragment}
varying float vSide,vFade,vPulse;varying vec3 vColor;
void main(){vec2 finish=tailFinish();float core=exp(-vSide*vSide*32.);float halo=exp(-vSide*vSide*4.)*.18;float alpha=(core*.8+halo)*vFade*vPulse*(1.-smoothstep(.82,1.,abs(vSide)))*finish.x*uRadiance;if(alpha<.001)discard;gl_FragColor=vec4(mix(vColor,vec3(1.,.85,.64),finish.y),alpha);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`;
const sparkVertex=common+`
void main(){float age=aAge*uLife,t=uTime-age;vec3 p=trailAt(t,aLed,aAge);float seed=aLed*17.13+t*1.7;if(uStyle>1.5){p+=vec3(sin(seed)*.10,.12,cos(seed*.83)*.1)*age;p+=vec3(sin(age*1.7+seed),sin(age*.7+seed),cos(age*1.2+seed))*.025*age;}vec4 mv=modelViewMatrix*vec4(p,1.);gl_Position=projectionMatrix*mv;gl_PointSize=clamp(uSize.y*.14/max(1.,-mv.z),2.,38.)*(1.-aAge*.5);vSide=0.;lightAt(t);vFade*=.78+.22*sin(seed*3.);}
`;
const sparkFragment=`
${tailFragment}
varying float vFade,vPulse;varying vec3 vColor;
void main(){vec2 p=gl_PointCoord*2.-1.;float r=dot(p,p);if(r>1.)discard;vec2 finish=tailFinish();float alpha=(exp(-r*22.)+exp(-r*4.)*.25)*vFade*vPulse*finish.x*uRadiance;if(alpha<.002)discard;gl_FragColor=vec4(mix(vColor,vec3(1.,.85,.64),finish.y),alpha);
#include <tonemapping_fragment>
#include <colorspace_fragment>
}`;
function trailGeometry(samples,ribbons) {
  const stride=ribbons?2:1, total=MAX_LIGHTS*(samples+1)*stride;
  const positions=new Float32Array(total*3),ages=new Float32Array(total),light=new Float32Array(total),side=new Float32Array(total);
  const indices=ribbons?new Uint32Array(MAX_LIGHTS*samples*6):null;
  for(let l=0;l<MAX_LIGHTS;l++)for(let i=0;i<=samples;i++)for(let s=0;s<stride;s++) {
    const k=(l*(samples+1)+i)*stride+s;ages[k]=i/samples;light[k]=l;side[k]=s?1:-1;
    if(ribbons&&s===0&&i<samples){const j=(l*samples+i)*6;indices.set([k,k+2,k+1,k+1,k+2,k+3],j);}
  }
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(positions,3));g.setAttribute('aAge',new THREE.BufferAttribute(ages,1));g.setAttribute('aLed',new THREE.BufferAttribute(light,1));
  if(ribbons){g.setAttribute('aSide',new THREE.BufferAttribute(side,1));g.setIndex(new THREE.BufferAttribute(indices,1));}
  return g;
}
const materialOptions={uniforms:U,transparent:true,toneMapped:false,depthWrite:false,depthTest:true,blending:THREE.AdditiveBlending};
const ribbons=new THREE.Mesh(trailGeometry(SAMPLES,true),new THREE.ShaderMaterial({...materialOptions,side:THREE.DoubleSide,vertexShader:ribbonVertex,fragmentShader:ribbonFragment}));
const sparks=new THREE.Points(trailGeometry(SPARK_SAMPLES,false),new THREE.ShaderMaterial({...materialOptions,vertexShader:sparkVertex,fragmentShader:sparkFragment}));
ribbons.frustumCulled=sparks.frustumCulled=false;scene.add(ribbons,sparks);
const rays=createRayMeshes(THREE,{common,tailFragment,uniforms:U,ribbonGeometry:ribbons.geometry,maxLights:MAX_LIGHTS});scene.add(...Object.values(rays.meshes));
const halo=new THREE.Mesh(new THREE.PlaneGeometry(14,14),new THREE.ShaderMaterial({transparent:true,depthWrite:false,vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.);}',fragmentShader:'varying vec2 vUv;void main(){float r=length(vUv-.5)*2.;gl_FragColor=vec4(.08,.23,.28,exp(-r*r*8.)*.24);}',blending:THREE.AdditiveBlending}));
halo.rotation.x=-Math.PI/2;halo.position.y=-4.1;scene.add(halo);
const flight=createFlight({scene,camera,uniforms:U,canvas});

function cancelMeasurement() {sample=null;report=null;$('measure').disabled=paused;$('measurement').textContent='';delete $('measurement').dataset.report;}
function syncView(){
  if(state.sculpture!=='gyre'&&state.view==='ride')state.view='outside';
  if(!state.flightEnabled&&['chase','pilot'].includes(state.view))state.view='outside';
  const ride=state.view==='ride';
  const flying=['chase','pilot'].includes(state.view),attached=ride||flying;
  if(state.view!==activeView){
    if(attached){if(activeView==='outside'){outsidePosition.copy(camera.position);outsideTarget.copy(controls.target);}setOrbit(false);}
    else {camera.up.set(0,1,0);camera.position.copy(outsidePosition);controls.target.copy(outsideTarget);const damping=controls.enableDamping;controls.enableDamping=false;updatingCamera=true;controls.update();updatingCamera=false;controls.enableDamping=damping;}
    activeView=state.view;
  }
  controls.enabled=!attached;$('orbit').disabled=attached;$('view').value=state.view;$('view').querySelector('[value="ride"]').disabled=state.sculpture!=='gyre';
  $('home').textContent=attached?'Outside view':'Home view';
  $('view-note').textContent=flying?(state.view==='pilot'?'Flying from the rear wing, with the squadron ahead.':'Following the lead craft through the light.'):(ride?'Fixed to the bent leg. Wind pulls the older light into your wake.':state.sculpture==='gyre'?'Step onto the L, or launch a squadron through its rays.':'Follow a squadron through the sculpture.');
  $('viewport').dataset.view=state.view;$('viewport').dataset.sculpture=state.sculpture;
  $('view-hint').innerHTML=flying?'FORMATION FLIGHT <i>↗</i><small>FOLLOWING THE LIGHT</small>':ride?'RIDING THE BENT LEG <i>↟</i><small>THE LIGHT BECOMES YOUR WAKE</small>':'DRAG TO ORBIT <i>↗</i><small>SCROLL TO EXPLORE</small>';
  camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad((flying?56:ride?46:39)/2))*Math.max(1,1.1/camera.aspect)));camera.updateProjectionMatrix();
}
function sync() {
  for(const id of sliders) {
    $(id).value=state[id];
    $(id+'-value').textContent=id==='petals'?String(state[id]):id==='wind'?`${state[id].toFixed(2)}×`:['weave','turbulence','tailAmount'].includes(id)?`${Math.round(state[id]*100)}%`:id==='stem'||id==='reach'?state[id].toFixed(2):id==='tailRate'?`${state[id].toFixed(1)} Hz`:id==='tilt'||id==='wobble'?`${state[id]}°`:id==='memory'?`${state[id].toFixed(1)} s`:id==='pulse'?(state.pulse===0?'Steady':`${state.pulse.toFixed(1)}×`):`${state[id].toFixed(id==='precession'?3:2)} rev/s`;
  }
  $('raySpread-value').textContent=Math.round(state.raySpread*100)+'%';$('radiance-value').textContent=Math.round(state.radiance*100)+'%';
  $('flightEnabled').checked=state.flightEnabled;$('flight-fields').hidden=!state.flightEnabled;$('formation').value=state.formation;$('flightCount').value=state.flightCount;
  for(const key of Object.keys(FLIGHT_RANGES))$(key+'-value').textContent=['flightBreak','flightBank'].includes(key)?Math.round(state[key]*100)+'%':key==='flightTrack'?`${Math.round(state[key]*(state.count-1))+1} / ${state.count}`:state[key].toFixed(2);
  flight.sync(state,paused);
  $('raySpread').disabled=!RAY_STYLES.includes(state.style);$('ray-note').textContent=RAY_NOTES[state.style]||'The original light. Try a new material on your favourite motion.';
  U.uRaySpread.value=state.raySpread;U.uRadiance.value=state.radiance;$('blackout').checked=state.blackout;viewport.classList.toggle('deep-black',state.blackout);halo.visible=!state.blackout;
  $('sculpture').value=state.sculpture;$('weave-fields').hidden=state.sculpture==='gyre';$('reactive').checked=state.reactive;
  $('stem').disabled=$('motion').disabled=state.sculpture!=='gyre';$('reach-label').textContent=state.sculpture==='gyre'?'Bent arm length':'Radial reach';
  for(const key of ['Weave','Petals','Wind','Turbulence'])U['u'+key].value=state[key[0].toLowerCase()+key.slice(1)];
  U.uWorld.value=['gyre','braid','pendulum'].indexOf(state.sculpture);
  mechanism.visible=$('mechanism').checked&&state.sculpture==='gyre';anchor.visible=strings.visible=$('mechanism').checked&&state.sculpture==='pendulum';
  syncView();
  $('count').value=state.count;$('palette').value=state.palette;$('motion').value=state.motion;$('tail').value=state.tail;
  U.uTail.value=['fade','flicker','dissolve'].indexOf(state.tail);
  for(const id of ['Stem','Reach','TailAmount','TailRate'])U['u'+id].value=state[id[0].toLowerCase()+id.slice(1)];
  $('tailAmount').disabled=$('tailRate').disabled=state.tail==='fade';
  stemRod.scale.y=state.stem/3.25;stemRod.position.x=state.stem/2;
  bendRod.scale.y=state.reach/1.6;bendRod.position.set(state.stem,0,state.reach/2);
  controls.minDistance=state.sculpture==='gyre'?Math.max(8,Math.hypot(state.stem,state.reach)*3.1):8;controls.maxDistance=Math.max(30,controls.minDistance*2.5);
  if(state.view==='outside'&&camera.position.distanceTo(controls.target)<controls.minDistance)camera.position.sub(controls.target).setLength(controls.minDistance).add(controls.target);
  const axial=state.motion!=='sweep';arm.rotation.z=axial?Math.PI/2:0;U.uAxial.value=axial?1:0;
  document.querySelectorAll('[data-style]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.style===state.style)));
  for(const [key,id] of [['Spin','spin'],['Precession','precession'],['Tilt','tilt'],['Wobble','wobble'],['Life','memory'],['Pulse','pulse'],['Count','count']])U['u'+key].value=state[id];
  U.uStyle.value=['silk','filigree','prism'].includes(state.style)?0:state.style==='beads'?1:2;
  const palette=PALETTES[state.palette];U.uA.value.setHex(palette[0]);U.uB.value.setHex(palette[1]);U.uC.value.setHex(palette[2]);
  ribbons.visible=state.style==='silk';sparks.visible=['beads','sparks'].includes(state.style);rays.sync(state.style,state.count);
  ribbons.geometry.setDrawRange(0,state.count*SAMPLES*6);sparks.geometry.setDrawRange(0,state.count*(SPARK_SAMPLES+1));leds.count=state.count;
}
function saveSettings() {
  const url=new URL(location.href);url.searchParams.set('study',$('preset').value);
  for(const id of [...sliders,'count','palette','style','motion','tail','sculpture','view','reactive','blackout','flightEnabled','flightCount','formation'])url.searchParams.set(id,String(state[id]));
  history.replaceState(null,'',url);
}
function setState(next,prefill=false) {
  Object.assign(state,next);clearedAt=time-(prefill||paused?state.memory:0);U.uClear.value=clearedAt;sync();saveSettings();cancelMeasurement();draw();
}
const descriptions={silk:'Fine threads, slowly folding through space.',lattice:'Different rhythms, woven into a field of light.',ember:'A turning ember, shedding a garden of sparks.',bloom:'Long violet arcs, opening and folding inward.',braid:'Three currents. One impossible knot of sea glass and light.',pendulum:'Suspended light, drawing flowers that never quite repeat.',wind:'A seat on the turning arm. Gold streaming into the wake.'};
function preset(id,restore=false) {if(!restore){flight.reset();setState({...FLIGHT_DEFAULTS,...RAY_DEFAULTS,...WORLD_DEFAULTS,...PRESETS[id]},true);if(state.view==='outside')home();resize();}$('study-title').textContent=state.name;$('study-description').textContent=descriptions[id];saveSettings();}
let savedPresets=[];
function presetMessage(message,error=false){$('preset-message').textContent=message;$('preset-message').style.color=error?'#ffc1b1':'';}
function renderPresetList(selected=''){
  const select=$('saved-presets');select.replaceChildren(new Option(savedPresets.length?'Choose a saved preset…':'No saved presets yet',''));
  for(const item of savedPresets)select.add(new Option(item.name,item.id));
  select.value=selected;$('update-preset').disabled=!selected;
}
function capturePreset(name,id=crypto.randomUUID()){
  return {id,name,study:$('preset').value,settings:{...state},flight:flight.snapshot(),resolution:$('resolution').value,mechanism:$('mechanism').checked,orbit,time,camera:{position:(activeView!=='outside'?outsidePosition:camera.position).toArray(),target:(activeView!=='outside'?outsideTarget:controls.target).toArray()}};
}
function storePreset(name,id){
  try {
    const item=capturePreset(name,id);savedPresets=savePreset(localStorage,item);renderPresetList(item.id);
    $('preset-form').hidden=true;$('study-title').textContent=item.name;
    $('study-description').textContent='Your own light study.';
    presetMessage(`Saved “${item.name}” in this browser.`);return true;
  } catch(e){presetMessage(`Could not save: ${e.message}`,true);return false;}
}
$('save-preset').addEventListener('click',()=>{
  $('preset-form').hidden=false;$('preset-name').value=savedPresets.length?`${state.name} ${savedPresets.length+1}`:state.name;
  $('preset-name').focus();$('preset-name').select();
});
$('cancel-preset').addEventListener('click',()=>{$('preset-form').hidden=true;$('save-preset').focus();});
$('preset-form').addEventListener('submit',e=>{
  e.preventDefault();const name=$('preset-name').value.trim();
  if(!name){$('preset-name').setCustomValidity('Give your preset a name.');$('preset-name').reportValidity();return;}
  if(storePreset(name))$('save-preset').focus();
});
$('preset-name').addEventListener('input',()=>$('preset-name').setCustomValidity(''));
$('update-preset').addEventListener('click',()=>{const item=savedPresets.find(p=>p.id===$('saved-presets').value);if(item)storePreset(item.name,item.id);});
$('saved-presets').addEventListener('change',()=>{
  const item=savedPresets.find(p=>p.id===$('saved-presets').value);$('update-preset').disabled=!item;
  if(!item)return;
  $('preset-form').hidden=true;$('preset').value=item.study;time=item.time;last=0;
  $('resolution').value=item.resolution;$('mechanism').checked=item.mechanism;music?.clear();harmony.fill(0);
  setState({...item.settings,name:PRESETS[item.study].name},true);
  // Discard the previous view's damping before restoring the saved camera.
  const damping=controls.enableDamping;controls.enableDamping=false;updatingCamera=true;controls.update();
  camera.up.set(0,1,0);camera.position.fromArray(item.camera.position);controls.target.fromArray(item.camera.target);controls.update();controls.enableDamping=damping;updatingCamera=false;
  outsidePosition.fromArray(item.camera.position);outsideTarget.fromArray(item.camera.target);
  // The next draw must attach immediately after restoring the outside camera.
  flight.reset(item.flight);
  setOrbit(item.orbit);resize();
  const url=new URL(location.href);url.searchParams.set('resolution',item.resolution);history.replaceState(null,'',url);
  $('study-title').textContent=item.name;$('study-description').textContent='Your own light study.';
  presetMessage(`Loaded “${item.name}”. Changes stay unsaved until you choose Update selected.`);
});
try {savedPresets=loadPresets(localStorage);renderPresetList();} catch(e){presetMessage(e.message,true);}
for(const id of sliders)$(id).addEventListener('input',()=>setState({[id]:Number($(id).value)},['stem','reach','tailAmount','tailRate','weave','petals','wind','turbulence','raySpread','radiance',...Object.keys(FLIGHT_RANGES)].includes(id)));
$('flightEnabled').addEventListener('change',()=>setState({flightEnabled:$('flightEnabled').checked,view:$('flightEnabled').checked?'chase':'outside'},true));
$('formation').addEventListener('change',()=>setState({formation:$('formation').value},true));
$('flightCount').addEventListener('change',()=>setState({flightCount:Number($('flightCount').value)},true));
$('blackout').addEventListener('change',()=>setState({blackout:$('blackout').checked},true));
for(const id of ['count','palette'])$(id).addEventListener('change',()=>setState({[id]:id==='count'?Number($(id).value):$(id).value}));
document.querySelectorAll('[data-style]').forEach(b=>b.addEventListener('click',()=>setState({style:b.dataset.style},true)));
$('preset').addEventListener('change',()=>{renderPresetList();preset($('preset').value);presetMessage('A starting point. Make it yours, then save a version.');});
document.querySelectorAll('[data-world]').forEach(b=>b.addEventListener('click',()=>{$('preset').value=b.dataset.world;renderPresetList();preset(b.dataset.world);presetMessage('A new world to explore. Your saved presets are still here.');}));
for(const id of ['sculpture','view'])$(id).addEventListener('change',()=>{const next={[id]:$(id).value};if(id==='view'&&['chase','pilot'].includes(next.view))next.flightEnabled=true;setState(next,true);if(id==='sculpture'&&state.view==='outside')home();draw();});
$('reactive').addEventListener('change',()=>{setState({reactive:$('reactive').checked},true);if(!state.reactive){harmony.fill(0);U.uHarmony.value.set(0,0,0);draw();}});
$('tail').addEventListener('change',()=>setState({tail:$('tail').value},true));
$('motion').addEventListener('change',()=>{setState({motion:$('motion').value},true);const u=new URL(location.href);u.searchParams.set('motion',state.motion);history.replaceState(null,'',u);});
$('mechanism').addEventListener('change',()=>{sync();cancelMeasurement();draw();});
$('clear').addEventListener('click',()=>{clearedAt=time;U.uClear.value=time;cancelMeasurement();draw();});
function setPaused(value) {
  paused=value;cancelAnimationFrame(raf);raf=0;last=0;intervals=[];cancelMeasurement();controls.enableDamping=!paused;
  $('pause').textContent=paused?'Resume render':'Pause render';$('pause').setAttribute('aria-pressed',String(paused));$('paused').hidden=!paused;
  if(!paused&&!document.hidden)raf=requestAnimationFrame(frame);
  updateStatus(0);
}
$('pause').addEventListener('click',()=>setPaused(!paused));
function setOrbit(value) {orbit=state.view!=='outside'?false:value;controls.autoRotate=orbit;$('orbit').setAttribute('aria-pressed',String(orbit));$('orbit').textContent=orbit?'Stop camera orbit':'Slow camera orbit';cancelMeasurement();}
$('orbit').addEventListener('click',()=>setOrbit(!orbit));
controls.addEventListener('start',()=>setOrbit(false));
controls.addEventListener('change',()=>{if(paused&&!updatingCamera)draw();});
$('home').addEventListener('click',()=>{const attached=state.view!=='outside';if(attached)setState({view:'outside'},true);else home();cancelMeasurement();draw();});
$('fullscreen').addEventListener('click',async()=>{try{if(document.fullscreenElement)await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch(e){fail(e);}});
if(params.get('resolution')==='4k')$('resolution').value='4k';
let dpr=devicePixelRatio;
function resize() {
  const r=viewport.getBoundingClientRect();dpr=devicePixelRatio;size=bufferSize(r.width,r.height,dpr,$('resolution').value);
  renderer.setSize(...size,false);
  camera.aspect=Math.max(1,r.width)/Math.max(1,r.height);
  syncView();U.uSize.value.set(...size);U.uWidth.value=2.4*size[1]/Math.max(1,r.height);cancelMeasurement();intervals=[];draw();updateStatus(0);
}
new ResizeObserver(resize).observe(viewport);
$('resolution').addEventListener('change',()=>{resize();const u=new URL(location.href);u.searchParams.set('resolution',$('resolution').value);history.replaceState(null,'',u);});
function updateStatus(fps) {$('status').textContent=`${size[0]} × ${size[1]} · ${paused?'paused':`${Math.round(fps)} fps`} · MSAA`;$('status').dataset.frames=String(frames);}
function draw(dt=0) {
  U.uTime.value=time;anglesAt(time,state,angles);precess.rotation.y=angles[0];tilted.rotation.z=angles[1];rotor.rotation.y=angles[2];
  U.uHarmony.value.fromArray(harmony);$('harmony-status').dataset.shape=harmony.map(v=>v.toFixed(3)).join(',');
  if(state.view==='ride'){const pose=riderPose(time,state);camera.position.fromArray(pose.position);camera.up.fromArray(pose.up);camera.lookAt(...pose.target);}
  for(let i=0;i<state.count;i++) {
    const u=(i+.5)/state.count;emitterAt(time,u,state,local,harmony);scratch.position.set(...local);scratch.updateMatrix();leds.setMatrixAt(i,scratch.matrix);
    const h=.5+.5*Math.sin(u*3.7+time*.14+harmony[2]*.8);color.copy(U.uA.value).lerp(U.uB.value,THREE.MathUtils.smoothstep(h,0,.6)).lerp(U.uC.value,THREE.MathUtils.smoothstep(h,.57,1));
    const wave=.5+.5*Math.sin(time*Math.PI*2*state.pulse*(.6+u*1.7)+u*19);
    const light=state.pulse===0?1:state.style==='silk'?.45+.55*wave:THREE.MathUtils.smoothstep(wave,.58,.94);
    color.multiplyScalar((.12+light*2.4)*state.radiance);leds.setColorAt(i,color);
  }
  if(strings.visible){const a=stringsGeometry.attributes.position;for(let i=0;i<3;i++){const led=Math.min(state.count-1,Math.floor(state.count*(i+1)/3)-1);emitterAt(time,(led+.5)/state.count,state,local,harmony);a.setXYZ(i*2,0,5.4,0);a.setXYZ(i*2+1,...local);}a.needsUpdate=true;}
  flight.update(dt,time,state,harmony,paused);
  leds.instanceMatrix.needsUpdate=true;leds.instanceColor.needsUpdate=true;renderer.render(scene,camera);frames++;canvas.dataset.frames=String(frames);canvas.dataset.resources=JSON.stringify(renderer.info.memory);
}
function frame(now) {
  raf=0;if(paused||document.hidden)return;
  const delta=last?now-last:0;last=now;
  if(devicePixelRatio!==dpr)resize();
  const dt=Math.min(delta/1000,.05);time+=dt;
  for(let i=0;i<3;i++)harmony[i]+=((state.reactive?harmonyGoal[i]:0)-harmony[i])*(1-Math.exp(-dt*1.7));
  if(controls.enabled)controls.update(dt);draw(dt);
  if(delta>0){intervals.push(delta);if(intervals.length>120)intervals.shift();}
  if(now-statusAt>600){updateStatus(intervals.length?1000/(intervals.reduce((a,b)=>a+b,0)/intervals.length):0);statusAt=now;}
  if(sample&&now>=sample.start) {
    if(sample.previous!==null)sample.values.push(now-sample.previous);sample.previous=now;
    const elapsed=now-sample.start;$('measurement').textContent=`Measuring ${Math.min(10,Math.floor(elapsed/1000))}/10 s`;
    if(elapsed>=10000) {
      const gl=renderer.getContext(),ext=gl.getExtension('WEBGL_debug_renderer_info');
      report={...frameStats(sample.values),width:size[0],height:size[1],style:state.style,sculpture:state.sculpture,view:state.view,wind:state.wind,lights:state.count,flightEnabled:state.flightEnabled,formation:state.formation,flightCount:state.flightCount,flightSpeed:state.flightSpeed,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,points:renderer.info.render.points,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,samples:gl.getParameter(gl.SAMPLES),gpu:ext?gl.getParameter(ext.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)};
      $('measurement').dataset.report=JSON.stringify(report);$('measurement').textContent=`${report.fps} fps · p95 ${report.p95Ms} ms`;$('measure').disabled=false;sample=null;
    }
  }
  raf=requestAnimationFrame(frame);
}
$('measure').addEventListener('click',()=>{sample={start:performance.now()+1000,previous:null,values:[]};$('measure').disabled=true;$('measurement').textContent='Warming up…';});
document.addEventListener('visibilitychange',()=>{cancelAnimationFrame(raf);raf=0;last=0;intervals=[];cancelMeasurement();if(!document.hidden&&!paused)raf=requestAnimationFrame(frame);});
reduced.addEventListener('change',()=>{if(reduced.matches){setOrbit(false);setPaused(true);}});
const initial=Object.hasOwn(PRESETS,params.get('study'))?params.get('study'):'silk';$('preset').value=initial;
music=mountGyreMusic({onNotes(values){values.forEach((v,i)=>harmonyGoal[i]=v);cancelMeasurement();if(paused){harmonyGoal.forEach((v,i)=>harmony[i]=state.reactive?v:0);draw();}},onEnable(){setState({reactive:true},true);}});
sync();resize();preset(initial,true);$('loading').hidden=true;setPaused(paused);
addEventListener('pagehide',e=>{if(e.persisted)return;cancelAnimationFrame(raf);music?.dispose();controls.dispose();const geometries=new Set(),materials=new Set();scene.traverse(o=>{if(o.geometry)geometries.add(o.geometry);if(o.material)materials.add(o.material);});geometries.forEach(g=>g.dispose());materials.forEach(m=>m.dispose());renderer.dispose();});
