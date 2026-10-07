// Instantaneous RK2 streamlines through any object exposing velocity(x,y,z,out).
// They are not stored pathlines. A fine SDF guards sub-grid visual clearance.
export function fanSeeds({count=72,origin=[-5,.055,0],up=[0,1,0],right=[0,0,1],radii=[.43,.92,1.41]}={}){
 const rows=radii.length,columns=Math.ceil(count/rows);
 return Array.from({length:count},(_,l)=>{
  const row=l%rows,col=Math.floor(l/rows),theta=.08+(Math.PI-.16)*(col+.2+row*.23)/columns,r=radii[row];
  return origin.map((v,a)=>v+r*(Math.sin(theta)*up[a]+Math.cos(theta)*right[a]));
 });
}
export function traceStreamlines(field,body,{count=72,segments=384,start=-5,end=7,clearance=.08,seeds=null,floor=.065}={}){
 seeds??=fanSeeds({count,origin:[start,.055,0]});count=seeds.length;
 const paths=new Float32Array(count*(segments+1)*4),a=[0,0,0],b=[0,0,0];
 let minDistance=Infinity,corrections=0;const step=.045;
 for(let l=0;l<count;l++){
  let p=seeds[l].slice();
  const raw=[p.slice()],arc=[0];
  for(let j=0;j<1200&&p[0]<end;j++){
   field.velocity(...p,a);const speed=Math.hypot(...a);
   if(speed<.02)break;const dt=step/Math.max(speed,.2);
   field.velocity(p[0]+a[0]*dt*.5,p[1]+a[1]*dt*.5,p[2]+a[2]*dt*.5,b);
   const q=[p[0]+b[0]*dt,p[1]+b[1]*dt,p[2]+b[2]*dt];q[1]=Math.max(floor,q[1]);
   if(body.sample(...q)<clearance){body.project(q,clearance);corrections++;}
   const len=Math.hypot(q[0]-p[0],q[1]-p[1],q[2]-p[2]);if(len<1e-6)break;
   arc.push(arc.at(-1)+len);raw.push(q);p=q;
   if(Math.abs(p[2])>5||p[1]>5)break;
  }
  // Arc-length resampling makes the existing ribbon renderer independent of
  // solver steps and integrates cleanly with other renderer adapters.
  let k=0;const length=arc.at(-1);
  for(let j=0;j<=segments;j++){
   const s=length*j/segments;while(k<arc.length-2&&arc[k+1]<s)k++;
   const next=Math.min(k+1,raw.length-1),t=(s-arc[k])/Math.max(1e-8,arc[next]-arc[k]),q=[0,1,2].map(a=>raw[k][a]*(1-t)+raw[next][a]*t);
   q[1]=Math.max(floor,q[1]);body.project(q,clearance);minDistance=Math.min(minDistance,body.sample(...q));
   field.velocity(...q,a);paths.set([...q,Math.hypot(...a)],(l*(segments+1)+j)*4);
  }
 }
 return {paths,minDistance,corrections};
}
