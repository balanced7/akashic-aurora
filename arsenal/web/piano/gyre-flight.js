import * as THREE from 'three';
import {FlightCourse,formationOffset} from './gyre-flight-motion.mjs';

// Scene adapter: original instanced craft, fixed-capacity wakes, one camera owner.
export function createFlight({scene,camera,uniforms,canvas}){
 const MAX=13,HISTORY=96,group=new THREE.Group();scene.add(group);group.visible=false;
 const course=new FlightCourse(),scratch=new THREE.Object3D(),matrix=new THREE.Matrix4(),right=new THREE.Vector3(),up=new THREE.Vector3(),forward=new THREE.Vector3(),colour=new THREE.Color();
 const vertices=[0,0,.25,-.055,.025,-.14,.055,.025,-.14, 0,0,.25,.055,.025,-.14,0,-.045,-.1, 0,0,.25,0,-.045,-.1,-.055,.025,-.14, -.055,.025,-.14,0,-.045,-.1,.055,.025,-.14, 0,.008,.12,-.19,-.015,-.13,-.045,.008,-.09, 0,.008,.12,.045,.008,-.09,.19,-.015,-.13];
 const hullGeometry=new THREE.BufferGeometry();hullGeometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));hullGeometry.computeVertexNormals();
 const hull=new THREE.InstancedMesh(hullGeometry,new THREE.MeshStandardMaterial({color:0x8da2b4,metalness:.7,roughness:.26,emissive:0x1e2040,emissiveIntensity:.3,side:THREE.DoubleSide}),MAX);
 const engines=new THREE.InstancedMesh(new THREE.SphereGeometry(.034,16,12),new THREE.ShaderMaterial({transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false,
  vertexShader:`varying vec3 vNormal,vView,vColour;void main(){vec4 mv=modelViewMatrix*instanceMatrix*vec4(position,1.);vNormal=normalMatrix*mat3(instanceMatrix)*normal;vView=-mv.xyz;vColour=instanceColor;gl_Position=projectionMatrix*mv;}`,
  fragmentShader:`varying vec3 vNormal,vView,vColour;void main(){float facing=max(0.,dot(normalize(vNormal),normalize(vView)));float core=pow(facing,12.);float alpha=smoothstep(0.,.5,facing)*(.14+.86*core);gl_FragColor=vec4(mix(vColour,vec3(1.),core*.65),alpha);
  #include <colorspace_fragment>
  }`}),MAX*2);
 hull.frustumCulled=engines.frustumCulled=false;hull.instanceMatrix.setUsage(THREE.DynamicDrawUsage);engines.instanceMatrix.setUsage(THREE.DynamicDrawUsage);group.add(hull,engines);
 const points=new Float32Array(MAX*2*HISTORY*3),heads=new Float32Array(MAX*2*3);
 const total=MAX*2*HISTORY*2,positions=new Float32Array(total*3),nexts=new Float32Array(total*3),ages=new Float32Array(total),sides=new Float32Array(total),ids=new Float32Array(total),indices=new Uint32Array(MAX*2*(HISTORY-1)*6);
 for(let strand=0;strand<MAX*2;strand++)for(let j=0;j<HISTORY;j++)for(let side=0;side<2;side++){const k=(strand*HISTORY+j)*2+side;ages[k]=j/(HISTORY-1);sides[k]=side?1:-1;ids[k]=Math.floor(strand/2);if(!side&&j<HISTORY-1)indices.set([k,k+2,k+1,k+1,k+2,k+3],(strand*(HISTORY-1)+j)*6);}
 const geometry=new THREE.BufferGeometry();for(const [name,data,size]of [['position',positions,3],['aNext',nexts,3],['aAge',ages,1],['aSide',sides,1],['aCraft',ids,1]])geometry.setAttribute(name,new THREE.BufferAttribute(data,size));geometry.setIndex(new THREE.BufferAttribute(indices,1));geometry.attributes.position.setUsage(THREE.DynamicDrawUsage);geometry.attributes.aNext.setUsage(THREE.DynamicDrawUsage);
 const wakeUniforms={uSize:uniforms.uSize,uWidth:uniforms.uWidth,uA:uniforms.uA,uB:uniforms.uB,uC:uniforms.uC,uRadiance:uniforms.uRadiance,uFilled:{value:0}};
 const wakes=new THREE.Mesh(geometry,new THREE.ShaderMaterial({uniforms:wakeUniforms,transparent:true,depthWrite:false,blending:THREE.AdditiveBlending,toneMapped:false,side:THREE.DoubleSide,
  vertexShader:`uniform vec2 uSize;uniform float uWidth,uFilled;attribute vec3 aNext;attribute float aAge,aSide,aCraft;varying float vAge,vSide,vCraft;void main(){vec4 p=modelViewMatrix*vec4(position,1.),q=modelViewMatrix*vec4(aNext,1.);float fade=smoothstep(.1,.35,-p.z);p.z=min(p.z,-.08);q.z=min(q.z,-.08);vec4 cp=projectionMatrix*p,cq=projectionMatrix*q;vec2 d=(cq.xy/cq.w-cp.xy/cp.w)*uSize,n=vec2(-d.y,d.x)/max(length(d),.0001);cp.xy+=n*aSide*uWidth*1.3*2./uSize*cp.w;gl_Position=cp;vAge=aAge>uFilled?1.:1.-(1.-aAge)*fade;vSide=aSide;vCraft=aCraft;}`,
  fragmentShader:`uniform vec3 uA,uB,uC;uniform float uRadiance;varying float vAge,vSide,vCraft;void main(){float profile=exp(-vSide*vSide*24.)+.18*exp(-vSide*vSide*3.);float alpha=profile*pow(1.-vAge,1.7)*uRadiance*.8;if(alpha<.001)discard;float h=fract(vCraft*.173);vec3 c=mix(mix(uA,uB,h),uC,.35);gl_FragColor=vec4(c,alpha);
  #include <colorspace_fragment>
  }`}));wakes.frustumCulled=false;group.add(wakes);
 const railGeometry=new THREE.BufferGeometry();railGeometry.setAttribute('position',new THREE.BufferAttribute(course.positions,3));const rail=new THREE.Line(railGeometry,new THREE.LineBasicMaterial({color:0x91baff,transparent:true,opacity:.18,depthWrite:false}));rail.frustumCulled=false;group.add(rail);
 let distance=0,clock=0,ring=0,filled=0,accumulator=0,signature='',formationSignature='',lastView='',statusAt=0;
 const slots=Array.from({length:MAX},()=>[0,0,0]);let slotsReady=false;
 const eye=new THREE.Vector3(),look=new THREE.Vector3(),camUp=new THREE.Vector3(),goalQuaternion=new THREE.Quaternion(),cameraMatrix=new THREE.Matrix4();
 function resetHistory(){filled=0;ring=0;accumulator=0;slotsReady=false;}
 function basis(frame){right.fromArray(frame.right);up.fromArray(frame.up);forward.fromArray(frame.forward);matrix.makeBasis(right,up,forward);scratch.quaternion.setFromRotationMatrix(matrix);scratch.position.fromArray(frame.position);}
 return {
  reset(value={}){distance=value.distance||0;clock=value.clock||0;course.firstRight=value.frame?[...value.frame.right]:null;course.firstTangent=value.frame?[...value.frame.tangent]:null;lastView='';resetHistory();},
  snapshot(){return {distance,clock,...(course.firstRight?{frame:{right:[...course.firstRight],tangent:[...course.firstTangent]}}:{})};},
  sync(state,paused=false){group.visible=state.flightEnabled;const key=[state.flightEnabled,state.sculpture,state.flightTrack,state.flightCount,state.spin,state.precession,state.wobble,state.tilt,state.memory,state.stem,state.reach,state.wind,state.turbulence,state.tail,state.tailAmount,state.style,state.raySpread,state.count,state.motion,state.weave,state.petals].join('|'),formationKey=[state.formation,state.flightSpread,state.flightSpacing,state.flightHeight,state.flightBreak].join('|');if(key!==signature||(paused&&formationKey!==formationSignature))resetHistory();signature=key;formationSignature=formationKey;hull.count=state.flightCount;engines.count=state.flightCount*2;geometry.setDrawRange(0,state.flightCount*2*(HISTORY-1)*6);},
  update(dt,time,state,harmony,paused=false){
   if(!state.flightEnabled)return;course.update(time,state,harmony);if(!course.stationary){distance+=dt*state.flightSpeed;clock+=dt;}
   const poses=[];const blend=dt>0?1-Math.exp(-dt*3):paused?1:0;
   for(let i=0;i<state.flightCount;i++){
    const goal=formationOffset(i,clock,state);for(let k=0;k<3;k++)slots[i][k]=slotsReady?THREE.MathUtils.lerp(slots[i][k],goal[k],blend):goal[k];
    const slot=slots[i],pose=course.sample(distance+slot[2]);pose.position=pose.position.map((v,k)=>v+pose.right[k]*slot[0]+pose.up[k]*slot[1]);poses.push(pose);basis(pose);
    scratch.scale.setScalar(state.view==='pilot'&&i===state.flightCount-1?0:1);scratch.updateMatrix();hull.setMatrixAt(i,scratch.matrix);
    const h=(i*.173)%1;colour.copy(uniforms.uA.value).lerp(uniforms.uB.value,h).lerp(uniforms.uC.value,.4).multiplyScalar(state.radiance*2.2);
    for(let side=0;side<2;side++){const p=pose.position.map((v,k)=>v+pose.right[k]*(side?.052:-.052)-pose.forward[k]*.125);heads.set(p,(i*2+side)*3);scratch.position.fromArray(p);scratch.updateMatrix();engines.setMatrixAt(i*2+side,scratch.matrix);engines.setColorAt(i*2+side,colour);}
   }slotsReady=true;hull.instanceMatrix.needsUpdate=true;engines.instanceMatrix.needsUpdate=true;engines.instanceColor.needsUpdate=true;
   accumulator+=dt;if(filled===0||accumulator>=1/45){accumulator%=1/45;ring=(ring+1)%HISTORY;for(let s=0;s<state.flightCount*2;s++)points.set(heads.subarray(s*3,s*3+3),(s*HISTORY+ring)*3);filled=Math.min(HISTORY,filled+1);}
   for(let s=0;s<state.flightCount*2;s++)for(let j=0;j<HISTORY;j++)for(let side=0;side<2;side++){
    const k=((s*HISTORY+j)*2+side)*3,source=(s*HISTORY+(ring-Math.min(j,filled-1)+HISTORY)%HISTORY)*3,next=(s*HISTORY+(ring-Math.min(j+1,filled-1)+HISTORY)%HISTORY)*3;
    positions.set(j===0?heads.subarray(s*3,s*3+3):points.subarray(source,source+3),k);nexts.set(points.subarray(next,next+3),k);
   }
   geometry.attributes.position.needsUpdate=geometry.attributes.aNext.needsUpdate=true;wakeUniforms.uFilled.value=(filled-1)/(HISTORY-1);railGeometry.attributes.position.needsUpdate=true;
   if(state.view==='chase'||state.view==='pilot'){
    const pilot=state.view==='pilot',pose=poses[pilot?state.flightCount-1:0],back=pilot ? .12 : 2.8+state.flightSpread*state.flightCount*.4,height=pilot ? .08 : .9+state.flightHeight;
    eye.fromArray(pose.position).addScaledVector(forward.fromArray(pose.forward),-back).addScaledVector(up.fromArray(pose.up),height);
    const ahead=course.sample(distance+(pilot?slots[state.flightCount-1][2]:0)+1.2);look.fromArray(ahead.position);if(pilot)look.addScaledVector(right.fromArray(pose.right),slots[state.flightCount-1][0]).addScaledVector(up,slots[state.flightCount-1][1]);
    const bend=THREE.MathUtils.clamp(new THREE.Vector3().fromArray(ahead.forward).dot(right.fromArray(pose.right)),-1,1);camUp.fromArray(pose.up).applyAxisAngle(forward.fromArray(pose.forward),-bend*state.flightBank*.6);
    cameraMatrix.lookAt(eye,look,camUp);goalQuaternion.setFromRotationMatrix(cameraMatrix);
    const a=lastView===state.view?(dt>0?1-Math.exp(-dt*5):paused?1:0):1;camera.position.lerp(eye,a);camera.quaternion.slerp(goalQuaternion,a);camera.up.copy(camUp);
   }
   lastView=state.view;
   if(dt===0||performance.now()-statusAt>200){statusAt=performance.now();canvas.dataset.flight=JSON.stringify({distance,clock,length:course.length,stationary:course.stationary,craft:state.flightCount,formation:state.formation,view:state.view,returnFraction:1-course.distances[course.steps]/Math.max(.001,course.length),camera:camera.position.toArray()});document.getElementById('flight-status').textContent=course.stationary?'This ray is still. Add spin or wobble to fly.':`${state.flightCount} lightcraft · ${state.formation==='ballet'?'formations unfolding':state.formation} · ray ${Math.round(state.flightTrack*(state.count-1))+1}`;}
  }
 };
}
