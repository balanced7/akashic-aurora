// Additional light materials share Gyre's analytical path and emission-time colour.
export const RAY_DEFAULTS=Object.freeze({raySpread:.55,radiance:1,blackout:false});
export const RAY_STYLES=Object.freeze(['filigree','prism','fireflies']);
export const RAY_NOTES={filigree:'Three fine filaments entwine around each ray. Spread opens the weave.',prism:'Translucent light with violet, rose and ice-blue edges. Spread opens the ribbons.',fireflies:'Little lights leave the arm and drift into darkness. Spread lengthens their comet tails.'};

export function createRayMeshes(THREE,{common,tailFragment,uniforms,ribbonGeometry,maxLights}){
 const material=(vertexShader,fragmentShader)=>new THREE.ShaderMaterial({uniforms,vertexShader,fragmentShader,transparent:true,depthWrite:false,depthTest:true,toneMapped:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending});
 const extra=`uniform float uRaySpread; attribute float aLane; varying float vLane;
 vec3 filament(float t,float age){float phase=t*2.8+aLed*.73+aLane*TAU/3.;float r=(.018+.12*uRaySpread)*smoothstep(0.,.17,age);return trailAt(t,aLed,age)+orient(vec3(cos(phase),sin(phase)*.65,sin(phase))*r,t);}
 void projectRay(vec3 pos,vec3 next,float side,float width){vec4 p=modelViewMatrix*vec4(pos,1.),q=modelViewMatrix*vec4(next,1.);float nearFade=smoothstep(.12,.5,-p.z);p.z=min(p.z,-.08);q.z=min(q.z,-.08);vec4 cp=projectionMatrix*p,cq=projectionMatrix*q;vec2 d=(cq.xy/cq.w-cp.xy/cp.w)*uSize;vec2 n=vec2(-d.y,d.x)/max(length(d),.0001);cp.xy+=n*side*width*2./uSize*cp.w;gl_Position=cp;vFade*=nearFade;vSide=side;vLane=aLane;}`;
 const filigreeVertex=common+extra+`attribute float aSide;
 void main(){float t=uTime-aAge*uLife;lightAt(t);vColor=mix(vColor,aLane<.5?uA:(aLane<1.5?uB:uC),.38);projectRay(filament(t,aAge),filament(t+.002,max(0.,aAge-.002/uLife)),aSide,uWidth*.72);}`;
 const filigreeFragment=tailFragment+`varying float vSide,vFade,vPulse,vLane;varying vec3 vColor;
 void main(){float edge=1.-smoothstep(.72,1.,abs(vSide));float profile=exp(-vSide*vSide*38.)*.78+exp(-vSide*vSide*5.)*.12;float glint=pow(.5+.5*sin(vStamp*3.8+vLed*1.7+vLane*2.1),16.);vec2 f=tailFinish();float alpha=profile*vFade*vPulse*f.x*(.95+.75*glint)*edge*uRadiance;if(alpha<.001)discard;gl_FragColor=vec4(mix(vColor,vec3(.8,.88,1.),glint*.16+f.y*.2),alpha);
 #include <colorspace_fragment>
 }`;
 const prismVertex=common+extra+`attribute float aSide;
 void main(){float t=uTime-aAge*uLife;lightAt(t);float fold=.45+.55*pow(.5+.5*sin(t*1.4+aLed*.7),2.);float width=uWidth*(2.+7.*uRaySpread)*fold;projectRay(trailAt(t,aLed,aAge),trailAt(t+.002,aLed,max(0.,aAge-.002/uLife)),aSide,width);}`;
 const prismFragment=tailFragment+`uniform vec3 uA,uB,uC;varying float vSide,vFade,vPulse;varying vec3 vColor;
 void main(){float edge=1.-smoothstep(.72,1.,abs(vSide));float band=.5+.5*sin(vStamp*1.1+vLed*.71+vSide*3.2);vec3 colour=mix(mix(uA,uB,smoothstep(.08,.64,band)),uC,smoothstep(.65,.96,band));colour=mix(colour,vColor,.22);float hair=exp(-pow((abs(vSide)-.6)*24.,2.))*.23;float core=exp(-vSide*vSide*60.)*.24;float film=(.025+.045*pow(.5+.5*sin(vStamp*4.+vSide*12.+vLed),4.))*exp(-vSide*vSide*2.);vec2 f=tailFinish();float alpha=(hair+core+film)*edge*vFade*vPulse*f.x*uRadiance;if(alpha<.001)discard;gl_FragColor=vec4(colour,alpha);
 #include <colorspace_fragment>
 }`;
 const cometVertex=common+`uniform float uRaySpread;attribute vec2 aCorner;varying vec2 vLocal;
 void main(){
  float rate=160./uLife,phase=fract(sin(aLed*73.13)*437.13),tick=floor(uTime*rate-phase)-aAge*159.;float t=(tick+phase)/rate,age=clamp((uTime-t)/uLife,0.,1.),seconds=age*uLife;
  float seed=aLed*17.13+t*1.7;vec3 drift=vec3(sin(seed)*.06,.08,cos(seed*.83)*.06);
  vec3 p=trailAt(t,aLed,age)+drift*seconds*(.4+uRaySpread)+vec3(sin(seed+seconds*.7),cos(seed*.8+seconds*.5),sin(seed*.7))*.018*seconds;
  vec3 tangent=at(t+.02,aLed)-at(t-.02,aLed)+drift*.4;
  vec4 mv=modelViewMatrix*vec4(p,1.),q=modelViewMatrix*vec4(p+tangent,1.);float nearFade=smoothstep(.12,.5,-mv.z);mv.z=min(mv.z,-.08);q.z=min(q.z,-.08);vec4 cp=projectionMatrix*mv,cq=projectionMatrix*q;vec2 d=(cq.xy/cq.w-cp.xy/cp.w)*uSize;d=length(d)<.001?vec2(0.,1.):normalize(d);vec2 n=vec2(-d.y,d.x);
  float px=clamp(uSize.y*.065/max(1.,-mv.z),2.,18.);float lengthPx=px*(3.+15.*uRaySpread)*(.55+.45*sin(seed)*sin(seed));
  cp.xy+=(d*aCorner.x*lengthPx+n*aCorner.y*px)*2./uSize*cp.w;gl_Position=cp;vLocal=aCorner;
  lightAt(t);vAge=age;vFade=pow(1.-age,1.05)*smoothstep(uClear-.025,uClear+.025,t)*nearFade;
  vFade*=.5+.5*pow(.5+.5*sin(t*3.1+aLed*2.7+seconds*.7),2.);
 }`;
 const cometFragment=tailFragment+`varying vec2 vLocal;varying float vFade,vPulse;varying vec3 vColor;
 void main(){float x=vLocal.x,y=vLocal.y;float tip=exp(-x*x*100.-y*y*14.);float plume=exp(x*4.)*(1.-smoothstep(-.07,.05,x))*exp(-y*y*7.)*.5;float edge=smoothstep(-1.,-.8,x)*(1.-smoothstep(.7,1.,abs(y)));vec2 f=tailFinish();float alpha=(tip+plume)*edge*vFade*vPulse*f.x*uRadiance*1.8;if(alpha<.001)discard;gl_FragColor=vec4(mix(vColor,vec3(.72,.84,1.),tip*.28),alpha);
 #include <colorspace_fragment>
 }`;
 const samples=1024,lanes=3,vertices=maxLights*lanes*(samples+1)*2;
 const ages=new Float32Array(vertices),leds=new Float32Array(vertices),sides=new Float32Array(vertices),laneData=new Float32Array(vertices),indices=new Uint32Array(maxLights*lanes*samples*6);
 for(let led=0;led<maxLights;led++)for(let lane=0;lane<lanes;lane++)for(let j=0;j<=samples;j++)for(let side=0;side<2;side++){
  const k=((led*lanes+lane)*(samples+1)+j)*2+side;ages[k]=j/samples;leds[k]=led;sides[k]=side?1:-1;laneData[k]=lane;
  if(!side&&j<samples)indices.set([k,k+2,k+1,k+1,k+2,k+3],((led*lanes+lane)*samples+j)*6);
 }
 function geometry(count,attributes,index){const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(count*3),3));for(const [key,[data,size]]of Object.entries(attributes))g.setAttribute(key,new THREE.BufferAttribute(data,size));g.setIndex(new THREE.BufferAttribute(index,1));return g;}
 const filigreeGeometry=geometry(vertices,{aAge:[ages,1],aLed:[leds,1],aSide:[sides,1],aLane:[laneData,1]},indices);
 const count=maxLights*160*4,ca=new Float32Array(count),cl=new Float32Array(count),corner=new Float32Array(count*2),ci=new Uint32Array(maxLights*160*6);
 for(let led=0;led<maxLights;led++)for(let j=0;j<160;j++){const base=(led*160+j)*4;for(let v=0;v<4;v++){ca[base+v]=j/159;cl[base+v]=led;corner.set([v<2?-1:.25,v%2?1:-1],(base+v)*2);}ci.set([base,base+2,base+1,base+1,base+2,base+3],(led*160+j)*6);}
 const cometGeometry=geometry(count,{aAge:[ca,1],aLed:[cl,1],aCorner:[corner,2]},ci);
 const meshes={filigree:new THREE.Mesh(filigreeGeometry,material(filigreeVertex,filigreeFragment)),prism:new THREE.Mesh(ribbonGeometry,material(prismVertex,prismFragment)),fireflies:new THREE.Mesh(cometGeometry,material(cometVertex,cometFragment))};
 for(const mesh of Object.values(meshes)){mesh.frustumCulled=false;mesh.visible=false;}
 return {meshes,sync(style,count){for(const [key,mesh]of Object.entries(meshes))mesh.visible=style===key;filigreeGeometry.setDrawRange(0,count*lanes*samples*6);cometGeometry.setDrawRange(0,count*160*6);}};
}
