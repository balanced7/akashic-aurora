// Portable animation + sampled-CFD cache. No DOM, Three.js or solver dependency.
const MAGIC='FLOWCLP1',MAX_BYTES=128*1024*1024,MAX_HEADER=131072;
const check=(ok,message)=>{if(!ok)throw new Error('Flow take: '+message);};
const finite=Number.isFinite,integer=(n,a,b)=>Number.isInteger(n)&&n>=a&&n<=b;
function hash(bytes,start=16){let h=2166136261;for(let i=start;i<bytes.length;i++)h=Math.imul(h^bytes[i],16777619);return h>>>0;}
function validate(h){
 check(h.version===1,'unsupported version');check(integer(h.streams,1,108)&&integer(h.segments,4,512),'invalid path dimensions');
 check(integer(h.frames,2,128),'invalid frame count');check(Array.isArray(h.times)&&h.times.length===h.frames,'invalid timestamps');
 check(h.times[0]===0&&h.times.every((t,i)=>finite(t)&&t>=0&&t<=180&&(!i||t>h.times[i-1])),'timestamps must increase from zero');
 const g=h.grid;check(g&&g.layout==='MAC-uvwp','unsupported field layout');
 check(Array.isArray(g.size)&&g.size.length===3&&g.size.every(n=>integer(n,3,256)),'invalid grid dimensions');
 check(Array.isArray(g.cells)&&g.cells.length===3&&g.cells.every((n,i)=>n===g.size[i]-1),'invalid MAC cells');
 check(Array.isArray(g.origin)&&g.origin.length===3&&g.origin.every(v=>finite(v)&&Math.abs(v)<1e6)&&finite(g.h)&&g.h>0&&g.h<1e4,'invalid grid coordinates');
 for(const key of ['pathsBounds','fieldBounds']){const b=h[key];check(b&&['min','max'].every(k=>Array.isArray(b[k])&&b[k].length===4&&b[k].every(v=>finite(v)&&Math.abs(v)<1e8))&&b.min.every((v,i)=>v<=b.max[i]),'invalid quantization bounds');}
 const pathLength=h.streams*(h.segments+1)*4,fieldLength=g.size.reduce((a,b)=>a*b,4),stride=pathLength+fieldLength;
 check(stride*h.frames*2<=MAX_BYTES,'recording exceeds 128 MB');return {pathLength,fieldLength,stride};
}
export function encodeFlowClip({streams,segments,grid,metadata={},frames}){
 check(Array.isArray(frames)&&frames.length>=2&&frames.length<=128,'need 2 to 128 frames');
 const bounds=key=>{
  const min=[Infinity,Infinity,Infinity,Infinity],max=[-Infinity,-Infinity,-Infinity,-Infinity];
  for(const f of frames){check(f[key] instanceof Float32Array,'expected Float32 samples');for(let i=0;i<f[key].length;i++){const v=f[key][i],a=i%4;check(finite(v),'non-finite sample');min[a]=Math.min(min[a],v);max[a]=Math.max(max[a],v);}}
  return {min,max};
 };
 const h={version:1,streams,segments,grid,frames:frames.length,times:frames.map(f=>f.t),simTimes:frames.map(f=>f.simTime),metadata,pathsBounds:bounds('paths'),fieldBounds:bounds('field')};
 const {pathLength,fieldLength,stride}=validate(h);
 for(const f of frames)check(f.paths.length===pathLength&&f.field.length===fieldLength,'inconsistent frame sizes');
 const json=new TextEncoder().encode(JSON.stringify(h));check(json.length<=MAX_HEADER,'metadata too large');
 const offset=Math.ceil((16+json.length)/4)*4,total=offset+stride*frames.length*2;check(total<=MAX_BYTES,'recording exceeds 128 MB');
 const buffer=new ArrayBuffer(total),bytes=new Uint8Array(buffer),view=new DataView(buffer);
 bytes.set(new TextEncoder().encode(MAGIC));view.setUint32(8,json.length,true);bytes.set(json,16);
 let cursor=offset;
 for(const f of frames)for(const key of ['paths','field']){const b=h[key+'Bounds'];for(let i=0;i<f[key].length;i++){const a=i%4,range=b.max[a]-b.min[a],q=range?Math.round((f[key][i]-b.min[a])/range*65535):0;view.setUint16(cursor,q,true);cursor+=2;}}
 view.setUint32(12,hash(bytes),true);return buffer;
}
export class FlowClip {
 constructor(buffer){
  check(buffer instanceof ArrayBuffer&&buffer.byteLength>=20&&buffer.byteLength<=MAX_BYTES,'invalid file size');
  const bytes=new Uint8Array(buffer),view=new DataView(buffer);check(new TextDecoder().decode(bytes.subarray(0,8))===MAGIC,'not a flowclip file');
  const len=view.getUint32(8,true);check(len>0&&len<=MAX_HEADER&&16+len<=buffer.byteLength,'invalid header size');
  check(hash(bytes)===view.getUint32(12,true),'integrity check failed');
  let h;try{h=JSON.parse(new TextDecoder().decode(bytes.subarray(16,16+len)));}catch{throw new Error('Flow take: malformed metadata');}
  const shape=validate(h),offset=Math.ceil((16+len)/4)*4;check(offset+shape.stride*h.frames*2===buffer.byteLength,'truncated or trailing data');
  Object.assign(this,shape,{buffer,view,header:h,offset,duration:h.times.at(-1)});
 }
 bracket(time){
  const times=this.header.times,t=Math.max(0,Math.min(this.duration,time));let a=0;
  while(a<times.length-2&&times[a+1]<=t)a++;return {a,b:a+1,alpha:(t-times[a])/(times[a+1]-times[a])};
 }
 decodeFrame(frame,key='paths',out){
  check(integer(frame,0,this.header.frames-1)&&['paths','field'].includes(key),'invalid frame request');
  const length=key==='paths'?this.pathLength:this.fieldLength,b=this.header[key+'Bounds'];out??=new Float32Array(length);check(out.length===length,'incorrect output size');
  const start=this.offset+(frame*this.stride+(key==='field'?this.pathLength:0))*2;
  for(let i=0;i<length;i++){const a=i%4;out[i]=b.min[a]+this.view.getUint16(start+i*2,true)/65535*(b.max[a]-b.min[a]);}return out;
 }
 sampleField(time,x,y,z,out=[0,0,0,0]){
  const {grid:g,fieldBounds:b}=this.header,{a,b:next,alpha}=this.bracket(time),[nx,ny,nz]=g.size;
  const xyz=[x,y,z].map((v,i)=>(v-g.origin[i])/g.h);
  for(let c=0;c<4;c++){
   const p=xyz.map((v,i)=>Math.max(0,Math.min(g.size[i]-1.00001,v-(c===i?0:.5)))),q=p.map(Math.floor),f=p.map((v,i)=>v-q[i]);let value=0;
   for(let dz=0;dz<2;dz++)for(let dy=0;dy<2;dy++)for(let dx=0;dx<2;dx++){
    const i=((q[0]+dx)+nx*((q[1]+dy)+ny*(q[2]+dz)))*4+c,w=(dx?f[0]:1-f[0])*(dy?f[1]:1-f[1])*(dz?f[2]:1-f[2]);
    const read=frame=>b.min[c]+this.view.getUint16(this.offset+(frame*this.stride+this.pathLength+i)*2,true)/65535*(b.max[c]-b.min[c]);
    value+=w*(read(a)*(1-alpha)+read(next)*alpha);
   }out[c]=value;
  }return out;
 }
}
export function clipPosition(elapsed,duration,mode='once'){
 if(mode==='bounce'){const p=((elapsed%(2*duration))+2*duration)%(2*duration)/duration;return duration*(.5-.5*Math.cos(Math.PI*p));}
 return Math.max(0,Math.min(duration,elapsed));
}
