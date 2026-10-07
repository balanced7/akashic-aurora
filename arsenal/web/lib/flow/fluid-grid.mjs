import {trilinear} from './distance-volume.mjs';

// Incompressible visual fluid, staggered MAC grid. No renderer or browser globals.
// Face velocities: U(i,j+.5,k+.5), V(i+.5,j,k+.5), W(i+.5,j+.5,k).
// Pressure solves A*q=-h^2*div(u); q is pressure impulse (p*dt/rho).
export class FluidGrid {
 constructor({nx=88,ny=28,nz=48,h=.14,origin=[-5.04,0,-3.36],distance=()=>100,wind=[1,0,0]}){
  if([nx,ny,nz].some(n=>!Number.isInteger(n)||n<3)||!(h>0))throw new Error('Invalid fluid grid');
  Object.assign(this,{nx,ny,nz,h,origin,wind:[...wind],time:0,steps:0});
  this.sx=nx+1;this.sz=(nx+1)*(ny+1);this.length=this.sz*(nz+1);
  const N=this.length;this.solid=new Uint8Array(N).fill(1);this.cells=[];
  for(let k=0;k<nz;k++)for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
   const p=i+this.sx*j+this.sz*k;if(distance(origin[0]+(i+.5)*h,origin[1]+(j+.5)*h,origin[2]+(k+.5)*h)>0){this.solid[p]=0;this.cells.push(p);}
  }
  this.cells=Int32Array.from(this.cells);this.neighbours=new Int32Array(N*6).fill(-1);this.degree=new Uint8Array(N);
  this.offsets=[-1,1,-this.sx,this.sx,-this.sz,this.sz];
  for(let k=0;k<nz;k++)for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){
   const p=i+this.sx*j+this.sz*k;if(this.solid[p])continue;
   const valid=[i>0,i<nx-1,j>0,j<ny-1,k>0,k<nz-1];
   for(let d=0;d<6;d++){const q=p+this.offsets[d];if(valid[d]&&!this.solid[q]){this.neighbours[p*6+d]=q;this.degree[p]++;}}
  }
  this.faces=[];
  for(let a=0;a<3;a++){
   const values=new Float32Array(N),next=new Float32Array(N),active=[],boundary=[],blocked=[];
   const lim=[nx,ny,nz];lim[a]++;const stride=[1,this.sx,this.sz][a];
   for(let k=0;k<lim[2];k++)for(let j=0;j<lim[1];j++)for(let i=0;i<lim[0];i++){
    const p=i+this.sx*j+this.sz*k,c=[i,j,k][a];
    if(c===0||c===[nx,ny,nz][a])boundary.push(p);
    else if(this.solid[p]||this.solid[p-stride])blocked.push(p);
    else active.push(p);
   }
   this.faces.push({values,next,active:Int32Array.from(active),boundary:Int32Array.from(boundary),blocked:Int32Array.from(blocked),stride,axis:a});
  }
  this.q=new Float32Array(N);this.r=new Float32Array(N);this.z=new Float32Array(N);this.d=new Float32Array(N);this.ad=new Float32Array(N);
  this.resetWind(wind);this.lastProjection={iterations:0,relativeResidual:0};
 }
 resetWind(wind){this.wind=[...wind];for(const f of this.faces){for(const p of f.active)f.values[p]=wind[f.axis];}this.boundaries();}
 boundaries(){for(const f of this.faces){for(const p of f.boundary)f.values[p]=f.axis===1?0:this.wind[f.axis];for(const p of f.blocked)f.values[p]=0;}this.padFaces();}
 padFaces(){
  // The shared storage has one extra plane in all three directions. Each face
  // component only uses one of those planes; extend the other two for sampling.
  const {nx,ny,nz,sx,sz}=this;
  for(const f of this.faces){const a=f.values;
   if(f.axis!==0)for(let k=0;k<=nz;k++)for(let j=0;j<=ny;j++){const p=nx+j*sx+k*sz;a[p]=a[p-1];}
   if(f.axis!==1)for(let k=0;k<=nz;k++)for(let i=0;i<=nx;i++){const p=i+ny*sx+k*sz;a[p]=a[p-sx];}
   if(f.axis!==2)for(let j=0;j<=ny;j++)for(let i=0;i<=nx;i++){const p=i+j*sx+nz*sz;a[p]=a[p-sz];}
  }
 }
 velocity(x,y,z,out=[0,0,0]){
  const {origin:o,h,sx,ny,nz}=this;const a=(x-o[0])/h,b=(y-o[1])/h,c=(z-o[2])/h;
  if(a<0||a>this.nx||b>ny||c<0||c>nz){out[0]=this.wind[0];out[1]=0;out[2]=this.wind[2];return out;}
  out[0]=trilinear(this.faces[0].values,sx,ny+1,nz+1,a,b-.5,c-.5);
  out[1]=trilinear(this.faces[1].values,sx,ny+1,nz+1,a-.5,b,c-.5);
  out[2]=trilinear(this.faces[2].values,sx,ny+1,nz+1,a-.5,b-.5,c);return out;
 }
 divergence(p){const [u,v,w]=this.faces;return (u.values[p+1]-u.values[p]+v.values[p+this.sx]-v.values[p]+w.values[p+this.sz]-w.values[p])/this.h;}
 multiply(input,out){const {cells,neighbours:n,degree:g}=this;for(let c=0;c<cells.length;c++){const p=cells[c];let sum=g[p]*input[p];for(let j=0;j<6;j++){const k=n[p*6+j];if(k>=0)sum-=input[k];}out[p]=sum;}}
 project(iterations=64,tolerance=1e-4){
  this.boundaries();const {q,r,z,d,ad,cells,degree:g,h}=this;q.fill(0);let mean=0;
  for(const p of cells){r[p]=-this.divergence(p)*h*h;mean+=r[p];}mean/=cells.length;
  let rz=0,b2=0;for(const p of cells){r[p]-=mean;z[p]=r[p]/Math.max(g[p],1);d[p]=z[p];rz+=r[p]*z[p];b2+=r[p]*r[p];}
  let residual=b2,used=0;
  for(let it=0;it<iterations&&residual>Math.max(1e-18,b2*tolerance*tolerance);it++){
   this.multiply(d,ad);let dad=0;for(const p of cells)dad+=d[p]*ad[p];if(dad<1e-25)break;
   const alpha=rz/dad;let nextRz=0;residual=0;
   for(const p of cells){q[p]+=alpha*d[p];r[p]-=alpha*ad[p];residual+=r[p]*r[p];z[p]=r[p]/Math.max(g[p],1);nextRz+=r[p]*z[p];}
   const beta=nextRz/rz;for(const p of cells)d[p]=z[p]+beta*d[p];rz=nextRz;used=it+1;
  }
  for(const f of this.faces)for(const p of f.active)f.values[p]-=(q[p]-q[p-f.stride])/h;
  this.padFaces();
  this.lastProjection={iterations:used,relativeResidual:Math.sqrt(residual/Math.max(b2,1e-30)),removedMean:mean};return this.lastProjection;
 }
 step(dt=.05,{iterations=48,force=null}={}){
  if(!Number.isFinite(dt)||dt<=0||dt>.1)throw new Error('Fluid step must be in (0, 0.1] seconds');
  const {nx,ny,nz,sx,sz,h,origin:o}=this,v=[0,0,0],acceleration=[0,0,0];
  // Transport all components from the same old field before swapping buffers.
  for(const f of this.faces){
   f.next.set(f.values);
   for(const p of f.active){
    const k=Math.floor(p/sz),j=Math.floor((p-k*sz)/sx),i=p-k*sz-j*sx;
    const x=o[0]+(i+(f.axis===0?0:.5))*h,y=o[1]+(j+(f.axis===1?0:.5))*h,z=o[2]+(k+(f.axis===2?0:.5))*h;
    this.velocity(x,y,z,v);
    const bx=(x-dt*v[0]-o[0])/h-(f.axis===0?0:.5),by=(y-dt*v[1]-o[1])/h-(f.axis===1?0:.5),bz=(z-dt*v[2]-o[2])/h-(f.axis===2?0:.5);
    let value=trilinear(f.values,sx,ny+1,nz+1,bx,by,bz);
    if(force){force(x,y,z,this.time,acceleration);value+=dt*acceleration[f.axis];}
    f.next[p]=value;
   }
  }
  for(const f of this.faces)[f.values,f.next]=[f.next,f.values];
  this.project(iterations);this.time+=dt;this.steps++;return this.lastProjection;
 }
 diagnostics(){
  let sum=0,max=0,solidFaceMax=0,maxSpeed=0;
  const [u,v,w]=this.faces;
  for(const p of this.cells){const d=this.divergence(p);sum+=d*d;max=Math.max(max,Math.abs(d));maxSpeed=Math.max(maxSpeed,.5*Math.hypot(u.values[p]+u.values[p+1],v.values[p]+v.values[p+this.sx],w.values[p]+w.values[p+this.sz]));}
  for(const f of this.faces)for(const p of f.blocked)solidFaceMax=Math.max(solidFaceMax,Math.abs(f.values[p]));
  return {grid:[this.nx,this.ny,this.nz],cellSize:this.h,fluidCells:this.cells.length,steps:this.steps,simTime:this.time,divergenceRms:Math.sqrt(sum/this.cells.length),divergenceMax:max,solidFaceMax,maxSpeed,...this.lastProjection};
 }
}
